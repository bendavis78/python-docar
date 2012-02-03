import json
import requests
from requests.auth import HTTPBasicAuth

from docar.fields import ForeignDocument, CollectionField
from docar.exceptions import HttpBackendError


class HttpBackendManager(object):

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
                for identifier in Document._meta.identifier:
                    kwargs[identifier] = related_instance[identifier]
                doc = Document(kwargs)
                # To avoid a new fetch, set the instance manualy, needed for
                # the uri method
                doc._backend_manager.instance = related_instance
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

    def fetch(self, document, *args, **kwargs):
        params = {}
        if 'username' in kwargs and 'password' in kwargs:
            # we enable authentication
            auth = HTTPBasicAuth(kwargs['username'], kwargs['password'])
            params['auth'] = auth
        response = requests.get(url=document.uri(), **params)

        self.response = response

        # FIXME: check if its a 404, then raise BackendDoesNotExist
        if (response.status_code > 399) and (response.status_code < 599):
            # we catch an error
            raise HttpBackendError(response.status_code,
                    json.loads(response.content))
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

        data = json.dumps(document._prepare_save())
        params['data'] = data
        # fetch the resource if its not yet fetched
        if not hasattr(self, 'response'):
            self.fetch(document, *args, **kwargs)

        # If the resource didnt exist, create it, otherwise update it
        if self.response.status_code == 404:
            # we create a new resource
            response = requests.post(
                    url=document.post_uri(),
                    **params)
        elif self.response.status_code == 200:
            response = requests.put(
                    url=document.uri(),
                    **params)
        self.response = response

    def delete(self, document, *args, **kwargs):
        # first make a GET request to see if the resource exists
        params = {}
        if 'username' in kwargs and 'password' in kwargs:
            # we enable authentication
            auth = HTTPBasicAuth(kwargs['username'], kwargs['password'])
            params['auth'] = auth
        if not hasattr(self, 'response'):
            self.fetch(document, *args, **kwargs)
        response = requests.delete(
                url=document.uri(), **params)
        self.response = response
