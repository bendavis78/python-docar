import json
import requests
from requests.auth import HTTPBasicAuth

from docar.fields import ForeignDocument, CollectionField


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
                related_list = instance[field.name]
                collection = field.Collection()
                for item in related_list:
                    doc = collection.document()
                    for elem in doc._meta.identifier:
                        setattr(doc, elem, item[elem])
                    # set the instance automaticaly, so that rendering and
                    # stuff is working okay
                    doc._backend_manager.instance = item
                    collection.add(doc)
                data[field.name] = collection
            elif field.name in instance:
                # Otherwise set the value of the field from the retrieved model
                # object
                data[field.name] = instance[field.name]
        return data

    def fetch(self, document, *args, **kwargs):
        params = {}
        if 'username' in kwargs and 'password' in kwargs:
            # we enable authentication
            auth = HTTPBasicAuth(kwargs['username'], kwargs['password'])
            params['auth'] = auth
        response = requests.get(url=document.uri(), **params)
        self.response = response

        # FIXME: check if its a 404, then raise BackendDoesNotExist
        # serialize from json and return a python dict
        if self.response.content:
            self.instance = json.loads(self.response.content)
            return self._to_dict(document)
        else:
            return {}

    def save(self, document, *args, **kwargs):
        data = json.dumps(document._prepare_save())

        # fetch the resource if its not yet fetched
        if not hasattr(self, 'response'):
            self.fetch(document, *args, **kwargs)

        # If the resource didnt exist, create it, otherwise update it
        if self.response.status_code == 404:
            # we create a new resource
            response = requests.post(
                    url=document.post_uri(),
                    data=data)
        elif self.response.status_code == 200:
            response = requests.put(
                    url=document.uri(),
                    data=data)
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
