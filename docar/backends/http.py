import json
import requests
from requests.auth import HTTPBasicAuth

from docar.fields import ForeignDocument, CollectionField
from docar.exceptions import HttpBackendError


class HttpBackendManager(object):
    SSL_CERT = None

    def _to_dict(self, document):
        instance = self.instance
        data = {}

        for field in document._meta.local_fields:
            if hasattr(document, "fetch_%s_field" % field.name):
                # We map the fieldname of the backend instance to the fieldname
                # of the document.
                fetch_field = getattr(document, "fetch_%s_field" % field.name)
                # just create a new field on the instance itself
                instance[field.name] = instance[fetch_field()]
            if hasattr(document, "map_%s_field" % field.name):
                # We map the fieldname of the backend instance to the fieldname
                # of the document.
                map_field = getattr(document, "map_%s_field" % field.name)
                # just create a new field on the instance itself
                instance[field.name], instance[map_field()]
            if not field.name in instance:
                data[field.name] = None
                continue
            if isinstance(field, ForeignDocument):
                kwargs = {}
                related_instance = instance[field.name]
                Document = field.Document
                kwargs = related_instance
                doc = Document(kwargs)
                # To avoid a new fetch, set the instance manualy, needed for
                # the uri method
                doc._backend_manager.instance = related_instance
                doc._backend_manager._to_dict(doc)
                doc.bound = True
                data[field.name] = doc
            elif isinstance(field, CollectionField):
                data[field.name] = self._get_collection(field,
                        context=document._context)
            elif field.name in instance:
                # Otherwise set the value of the field from the retrieved model
                # object
                data[field.name] = instance[field.name]
        return data

    def _get_collection(self, field, context={}):
        # FIXME: This relies on the fact that fetch has been called already
        instance = self.instance

        # create a new collection first
        collection = field.Collection()

        # create a document for each item in the m2m relation
        relation = instance[field.name]

        for item in relation:
            select_dict = {}
            # we first create an empty document, to have access to the fetch
            # methods
            doc = collection.document()
            for elem in collection.document._meta.identifier:
                if hasattr(doc, "fetch_%s_field" % elem):
                    fetch_field = getattr(doc, "fetch_%s_field" % elem)
                    select_dict[elem] = fetch_field()
                else:
                    select_dict[elem] = item[elem]
            # now we request the actual document, bound to a backend resource
            doc = collection.document(select_dict)
            # We dont need to fetch the object again
            doc._backend_manager.instance = item
            # we shortcut here the fetch mechanism, turn it into a dict
            # representation on set the attributes correctly
            obj = doc._backend_manager._to_dict(doc)
            for k, v in obj.iteritems():
                setattr(doc, k, v)
            collection.add(doc)
        return collection

    def _get_uri(self, verb, document):
        if hasattr(document, "%s_uri" % verb):
            # we found a specific uri method for this verb
            uri_method = getattr(document, "%s_uri" % verb)
            return uri_method()
        else:
            return document.uri()

    def fetch(self, document, *args, **kwargs):
        params = {}
        if 'username' in kwargs and 'password' in kwargs:
            # we enable authentication
            auth = HTTPBasicAuth(kwargs['username'], kwargs['password'])
            params['auth'] = auth
        if self.SSL_CERT:
            params['verify'] = self.SSL_CERT
        response = requests.get(url=self._get_uri('get', document), **params)

        self.response = response

        # FIXME: check if its a 404, then raise BackendDoesNotExist
        if (response.status_code > 399) and (response.status_code < 599):
            # we catch an error
            raise HttpBackendError(response.status_code,
                    response.content)
        # serialize from json and return a python dict
        if self.response.content:
            self.instance = json.loads(self.response.content)
            return self._to_dict(document)
        else:
            return {}

    def save(self, document, *args, **kwargs):
        params = {}

        if 'username' in kwargs and 'password' in kwargs:
            # we enable authentication
            auth = HTTPBasicAuth(kwargs['username'], kwargs['password'])
            params['auth'] = auth

        doc_state = document._prepare_save()

        for field in document._meta.local_fields:
            name = field.name
            if field.name not in doc_state:
                continue
            if hasattr(document, "map_%s_field" % field.name):
                # we map the attribute name
                map_field = getattr(document, "map_%s_field" % field.name)
                doc_state[map_field()] = getattr(document, field.name)
                name = map_field()
                setattr(document, name, doc_state[name])
            if hasattr(field, 'Collection'):
                coll = getattr(document, name)
                doc_state[name] = coll._prepare_render()
            elif hasattr(field, 'Document'):
                doc = getattr(document, name)
                doc_state[name] = doc._prepare_render()

        data = json.dumps(doc_state)
        params['data'] = data

        if self.SSL_CERT:
            params['verify'] = self.SSL_CERT

        # fetch the resource if its not yet fetched. Catch for a backend error,
        # but do create the resource if the error is a 404 NOT FOUND return
        # code.
        if not hasattr(self, 'response'):
            try:
                document.fetch(*args, **kwargs)
            except HttpBackendError as e:
                if e[0] == 404:
                    # we create a new resource
                    response = requests.post(
                        url=self._get_uri('post', document),
                        **params)
                    if response.status_code > 399 and \
                            response.status_code < 599:
                        # we catch an error
                        raise HttpBackendError(response.status_code,
                                response.content)
                    return
                else:
                    # Its some other error, so we just raise it again.
                    raise e
        # We update an existing resource
        response = requests.put(
                url=self._get_uri('put', document),
                **params)

        if response.status_code > 399 and \
                response.status_code < 599:
            # we catch an error
            raise HttpBackendError(response.status_code,
                    response.content)

        self.response = response

    def delete(self, document, *args, **kwargs):
        params = {}
        if 'username' in kwargs and 'password' in kwargs:
            # we enable authentication
            auth = HTTPBasicAuth(kwargs['username'], kwargs['password'])
            params['auth'] = auth

        if self.SSL_CERT:
            params['verify'] = self.SSL_CERT

        # first make a GET request to see if the resource exists
        #if not hasattr(self, 'response'):
        #    self.fetch(document, *args, **kwargs)
        response = requests.delete(
                url=self._get_uri('delete', document), **params)

        if response.status_code > 399 and \
                response.status_code < 599:
            # we catch an error
            raise HttpBackendError(response.status_code,
                    response.content)

        self.response = response
