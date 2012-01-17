import json
import requests


class HttpBackendManager(object):

    def fetch(self, document):
        response = requests.get(url=document.uri())
        self.response = response

        # serialize from json and return a python dict
        return json.loads(self.response.content)
