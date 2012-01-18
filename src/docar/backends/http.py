import json
import requests


class HttpBackendManager(object):

    def fetch(self, document):
        response = requests.get(url=document.uri())
        self.response = response

        # serialize from json and return a python dict
        return json.loads(self.response.content)

    def save(self, document):
        data = json.dumps(document._save_state())
        response = requests.put(
                url=document.uri(),
                data=data)
        self.response = response
