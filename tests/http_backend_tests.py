import unittest
import json

from nose.tools import eq_, ok_
from mock import patch, Mock
from requests.auth import HTTPBasicAuth

from docar.backends import BackendManager, HttpBackendManager
from docar import Document, Collection, fields


class when_a_http_backend_manager_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.request_patcher = patch('docar.backends.http.requests')
        self.mock_request = self.request_patcher.start()

    def tearDown(self):
        self.request_patcher.stop()

    def it_can_fetch_resources_from_a_remote_endpoint(self):
        mock_resp = Mock(name="mock_response")
        expected = {'id': 1}
        mock_resp.content = json.dumps(expected)

        self.mock_request.get.return_value = mock_resp

        manager = BackendManager('http')

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'http://location'

        doc = Doc({'id': 1})

        # the http manager returns the response as python dict
        content = manager.fetch(doc)

        # make sure we are working with correct expectations
        eq_(HttpBackendManager, type(manager))
        eq_(mock_resp, manager.response)
        ok_(isinstance(content, dict))
        eq_([('get', {'url': doc.uri()})],
                self.mock_request.method_calls)

    def it_can_delete_resources_from_a_remote_endpoint(self):
        mock_resp = Mock(name="mock_response")
        expected = {'id': 1}
        mock_resp.content = json.dumps(expected)

        self.mock_request.delete.return_value = mock_resp

        manager = BackendManager('http')

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'http://location'

        doc = Doc({'id': 1})

        manager.delete(doc)

        # make sure we are working with correct expectations
        eq_(HttpBackendManager, type(manager))
        eq_([
            ('delete', {'url': doc.uri()})
            ],
                self.mock_request.method_calls)

    @patch('docar.backends.http.HTTPBasicAuth')
    def it_can_take_credentials_as_arguments(self, mock_auth):
        auth_token = HTTPBasicAuth('crito', 'secret')
        mock_auth.return_value = auth_token

        mock_resp = Mock(name="mock_response")
        expected = {'id': 1}
        mock_resp.status_code = 200
        mock_resp.content = json.dumps(expected)

        self.mock_request.get.return_value = mock_resp
        self.mock_request.delete.return_value = mock_resp
        self.mock_request.put.return_value = mock_resp

        manager = BackendManager('http')

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'http://location'

        doc = Doc({'id': 1})

        # the http manager returns the response as python dict
        content = manager.fetch(doc, username='crito', password='secret')
        manager.delete(doc, username='crito', password='secret')
        manager.save(doc, username='crito', password='secret')

        # make sure we are working with correct expectations
        eq_(HttpBackendManager, type(manager))
        eq_(mock_resp, manager.response)
        ok_(isinstance(content, dict))
        eq_([
            ('get', {'url': doc.uri(), 'auth': auth_token}),
            ('delete', {'url': doc.uri(), 'auth': auth_token}),
            ('put', {'url': doc.uri(), 'data': '{"id": 1}',
                'auth': auth_token})],
                self.mock_request.method_calls)

    def it_can_create_new_remote_resources(self):
        mock_get = Mock(name="mock_get")
        mock_get.status_code = 404
        mock_get.content = ''
        expected = {'id': 1}
        mock_post = Mock(name="mock_post")
        mock_post.status_code = 201
        mock_post.content = json.dumps(expected)

        self.mock_request.get.return_value = mock_get
        self.mock_request.post.return_value = mock_post

        manager = BackendManager('http')

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'http://location'

            post_uri = uri

        doc = Doc({'id': 1})

        # create a new remote resource
        manager.save(doc)

        # creating a new resource should first return a 404 on a get request,
        # then a 201 on creation
        eq_([
            ('get', {'url': 'http://location'}),
            ('post', {'url': 'http://location',
                'data': json.dumps(expected)})],
            self.mock_request.method_calls)


class when_a_http_client_document_is_instantiated(unittest.TestCase):
    def setUp(self):
        self.request_patcher = patch('docar.backends.http.requests')
        self.mock_request = self.request_patcher.start()

    def tearDown(self):
        self.request_patcher.stop()

    def it_can_bind_itself_by_fetching_a_representation(self):
        class Other(Document):
            other = fields.StringField()

            class Meta:
                backend_type = 'http'
                identifier = 'other'

            def uri(self):
                return "http://col_location"

        class Other2(Document):
            other = fields.StringField()

            class Meta:
                backend_type = 'http'
                identifier = 'other'

            def uri(self):
                return "http://other_location"

        class OtherCol(Collection):
            document = Other

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()
            pub = fields.BooleanField()
            ext = fields.ForeignDocument(Other, inline=True)
            ext2 = fields.ForeignDocument(Other2)
            col = fields.CollectionField(OtherCol)
            optional = fields.StringField()
            fetched = fields.StringField()

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'http://location'

            def fetch_fetched_field(self):
                return 'fetch'

        doc = Doc({'id': 1})

        expected_other2 = {
                'other': 'document2'
                }
        expected = {
                'id': 1,
                'name': 'hello',
                'pub': True,
                'ext': {
                    'other': 'document'
                    },
                'ext2': expected_other2,
                'col': [
                    {'other': 'first'},
                    {'other': 'second'},
                    ],
                'fetched': 'jaja'
                }
        response_doc = Mock(name='mock_http_response')
        response_doc.content = json.dumps(expected)
        response_doc.status_code = 200

        response_other = Mock(name='mock_http_other_response')
        response_other.content = json.dumps(expected_other2)
        response_other.status_code = 200

        response_col1 = Mock(name='mock_http_other_response')
        response_col1.content = json.dumps(expected['col'][0])
        response_col1.status_code = 200

        response_col2 = Mock(name='mock_http_other_response')
        response_col2.content = json.dumps(expected['col'][1])
        response_col2.status_code = 200

        responses = [response_col1, response_col2, response_other, response_doc]
        def response_side_effect(*args, **kwargs):
            return responses.pop()

        # set the return value of the GET request
        self.mock_request.get.side_effect = response_side_effect

        # Make sure the name is not set right now
        eq_(expected['id'], doc.id)
        eq_(None, doc.name)

        # fetch the document from the HTTP backend, (is_bound = True)
        ret = doc._backend_manager.fetch(doc)

        eq_(expected['id'], ret['id'])
        eq_(expected['name'], ret['name'])
        eq_(expected['pub'], ret['pub'])
        eq_(expected['fetched'], ret['fetched'])
        eq_(expected_other2, ret['ext2'])
        eq_(None, ret['optional'])

        # we should have made one GET request
        eq_([('get', {'url': 'http://location'}),
            ('get', {'url': 'http://other_location'}),
            ('get', {'url': 'http://col_location'}),
            ('get', {'url': 'http://col_location'}),
            ],
                self.mock_request.method_calls)

    def it_can_update_the_document_on_the_remote_backend(self):
        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'http://location'

        doc = Doc({'id': 1})

        expected = {
                'id': 1,
                'name': 'other',
                }

        response = Mock(name='mock_http_response')
        response.content = json.dumps(expected)
        response.status_code = 200

        # set the return value of the GET request
        self.mock_request.get.return_value = response
        self.mock_request.put.return_value = response

        doc.update({'name': 'other'})

        # we should have made one GET and one PUT request
        eq_([('get', {'url': 'http://location'}),
            ('put', {'url': 'http://location', 'data': json.dumps(expected)})],
                self.mock_request.method_calls)
        eq_('other', doc.name)

    def it_can_construct_correct_json_messages_with_nested_documents(self):
        class Doc1(Document):
            id = fields.NumberField()


class when_a_http_backend_talks_to_an_api_endpoint(unittest.TestCase):
    def setUp(self):
        self.request_patcher = patch('docar.backends.http.requests')
        self.mock_request = self.request_patcher.start()

    def tearDown(self):
        self.request_patcher.stop()

    def it_can_construct_different_uris_for_different_http_verbs(self):
        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def post_uri(self):
                return 'post'

            def get_uri(self):
                return 'get'

            def uri(self):
                return 'uri'

        manager = BackendManager('http')
        doc = Doc({'id': 1})

        # First make sure we can retrieve the specific uri's for this http verb
        eq_('post', manager._get_uri('post', doc))
        eq_('get', manager._get_uri('get', doc))

        # And now return the generic uri for a non specified verb
        eq_('uri', manager._get_uri('put', doc))

    def it_can_construct_a_special_uri_for_fetch_operations(self):
        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def get_uri(self):
                return 'get'

        manager = BackendManager('http')
        doc = Doc({'id': 1})

        expected = {
                'id': 1,
                'name': 'other',
                }

        response = Mock(name='mock_http_response')
        response.content = json.dumps(expected)
        response.status_code = 200

        # set the return value of the GET request
        self.mock_request.get.return_value = response

        # now make the fetch operation
        manager.fetch(doc)

        # we should have made one GET and one PUT request
        eq_([('get', {'url': 'get'})],
                self.mock_request.method_calls)

    def it_can_construct_a_special_uri_for_update_operations(self):
        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def get_uri(self):
                return 'get'

            def put_uri(self):
                return 'put'

        manager = BackendManager('http')
        doc = Doc({'id': 1})

        expected = {'id': 1}

        response = Mock(name='mock_http_response')
        response.status_code = 200

        # set the return value of the GET request and the PUT request
        self.mock_request.put.return_value = response

        response.content = json.dumps(expected)
        self.mock_request.get.return_value = response

        # now make the fetch operation
        manager.save(doc)

        # we should have made one GET and one PUT request
        eq_([('get', {'url': 'get'}),
            ('put', {'url': 'put', 'data': json.dumps(expected)})],
                self.mock_request.method_calls)

    def it_can_construct_a_special_uri_for_create_operations(self):
        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'get'

            def post_uri(self):
                return 'post'

        manager = BackendManager('http')
        doc = Doc({'id': 1})

        expected = {'id': 1}

        response = Mock(name='mock_http_response')
        response.status_code = 404

        # set the return value of the GET request and the PUT request
        self.mock_request.get.return_value = response

        response = Mock(name='mock_http_post_response')
        response.status_code = 201
        response.content = json.dumps(expected)
        self.mock_request.post.return_value = response

        # now make the fetch operation
        manager.save(doc)

        # we should have made one GET and one POST request
        eq_([('get', {'url': 'get'}),
            ('post', {'url': 'post', 'data': json.dumps(expected)})],
                self.mock_request.method_calls)

    def it_can_construct_a_special_uri_for_delete_operations(self):
        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'get'

            def delete_uri(self):
                return 'delete'

        manager = BackendManager('http')
        doc = Doc({'id': 1})

        expected = {'id': 1}

        response = Mock(name='mock_http_response')
        response.status_code = 200

        # set the return value of the GET request and the DELETE request
        self.mock_request.delete.return_value = response
        response.content = json.dumps(expected)
        self.mock_request.get.return_value = response

        # now make the fetch operation
        manager.delete(doc)

        # we should have made one GET and one PUT request
        eq_([('delete', {'url': 'delete'})],
                self.mock_request.method_calls)
