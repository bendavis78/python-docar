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
        return json.loads(self.response.content)

    def save(self, document):
        data = json.dumps(document._save_state())
        response = requests.put(
                url=document.uri(),
                data=data)
        self.response = response
