import json
import requests
from requests.auth import HTTPBasicAuth


class HttpBackendManager(object):

    def fetch(self, document, *args, **kwargs):
        params = {}
        if 'username' in kwargs and 'password' in kwargs:
            # we enable authentication
            auth = HTTPBasicAuth(kwargs['username'], kwargs['password'])
            params['auth'] = auth
        response = requests.get(url=document.uri(), **params)
        self.response = response

        # serialize from json and return a python dict
        if self.response.content:
            return json.loads(self.response.content)
        else:
            return {}

    def save(self, document, *args, **kwargs):
        data = json.dumps(document._prepare_save())
        # first make a GET request to see if the resource exists
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
