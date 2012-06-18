""" http backend for docar

The http backend constructs JSON messages from the documents and sends them to
an API endpoint. It can receive again JSON messages and construct documents
from it. Its meant to be complimentary used with docar on the server. A
document send from the server to the client with document.to_json() should have
the right format to be understood by this backend.

"""
import json
import requests
from requests.auth import HTTPBasicAuth

from docar.fields import ForeignDocument, CollectionField
from docar.exceptions import HttpBackendError, BackendDoesNotExist


class HttpBackendManager(object):
    SSL_CERT = None

    def _to_dict(self, document):
        instance = self.instance
        data = {}

        for field in document._meta.local_fields:
            instance_field_name = field.name
            if hasattr(document, "map_%s_field" % field.name):
                # We map the fieldname of the backend instance to the fieldname
                # of the document.
                map_field = getattr(document, "map_%s_field" % field.name)
                # just create a new field on the instance itself
                instance_field_name = map_field()
            if not field.name in instance:
                data[field.name] = None
                continue
            if isinstance(field, ForeignDocument):
                kwargs = {}
                related_instance = instance[instance_field_name]
                if field.inline:
                    # The field is rendered inline, so we dont have to fetch it
                    # again.
                    data[field.name] = related_instance
                    continue
                # Fetch the document again to create a dict from it
                Document = field.Document
                kwargs = related_instance
                doc = Document(kwargs, context=document._context)
                # To avoid a new fetch, set the instance manualy, needed for
                # the uri method
                if self._get_uri('get', doc):
                    data[field.name] = doc._backend_manager.fetch(doc, **self.kwargs)
                else:
                    data[field.name] = related_instance
            elif isinstance(field, CollectionField):
                if field.inline:
                    data[field.name] = instance[instance_field_name]
                else:
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
                # if hasattr(doc, "fetch_%s_field" % elem):
                #     fetch_field = getattr(doc, "fetch_%s_field" % elem)
                #     select_dict[elem] = fetch_field()
                # else:
                select_dict[elem] = item[elem]
            # now we request the actual document, bound to a backend resource
            doc = collection.document(select_dict, context=context)
            # # We dont need to fetch the object again
            doc._backend_manager.instance = item
            if (hasattr(self, 'username') and hasattr(self, 'password')):
                doc.fetch(username=self.username, password=self.password)
            else:
                doc.fetch()
            collection.add(doc)
        return collection._to_dict()

    def _get_uri(self, verb, document):
        if hasattr(document, "%s_uri" % verb):
            # we found a specific uri method for this verb
            uri_method = getattr(document, "%s_uri" % verb)
            return uri_method()
        elif hasattr(document, "uri"):
            return document.uri()
        else:
            return False

    def fetch(self, document, *args, **kwargs):
        """Fetch the resource as a JSON message from an HTTP endpoint.

        It requests the resource using HTTP GET. A JSON message is expected and
        parsed. If ``username`` and ``password`` are specified, it can use HTTP
        basic authentication.
        """
        params = {}
        self.kwargs = kwargs

        # If we have HTTP basic auth, you can apply username and password
        if 'username' in kwargs and 'password' in kwargs:
            # we enable authentication
            self.username = kwargs['username']
            self.password = kwargs['password']
            auth = HTTPBasicAuth(kwargs['username'], kwargs['password'])
            params['auth'] = auth
        if self.SSL_CERT:
            params['verify'] = self.SSL_CERT

        # Make the http request
        #FIXME: Needs some exception handling probably
        response = requests.get(url=self._get_uri('get', document), **params)
        self.response = response

        # If the response is a 404, than the resource couldn't be found
        # we define its own exception, cause in save we catch this one to
        # determine whether to create a new or update an existing resource
        if response.status_code == 404:
            raise BackendDoesNotExist(response.status_code,
                    response.content)

        # Responses with a code of 4XX or 5XX are raising an error
        if (response.status_code > 399) and (response.status_code < 599):
            # we catch an error
            raise HttpBackendError(response.status_code,
                    response.content)

        # serialize from json and return a python dict
        if self.response.content:
            #FIXME: Handle a ValueError in case its not valid JSON
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

        doc_state = document._save()

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
                doc_state[name] = coll._to_dict()
            elif hasattr(field, 'Document'):
                doc = getattr(document, name)
                doc_state[name] = doc._to_dict()

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
            except BackendDoesNotExist:
                # If the resource hasn't been found, we assume we create a new
                # one, and make a post request. Otherwise we skip to a put
                # request.
                response = requests.post(
                    url=self._get_uri('post', document),
                    **params)
                if response.status_code > 399 and \
                        response.status_code < 599:
                    # we catch an error
                    raise HttpBackendError(response.status_code,
                            response.content)
                return
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
