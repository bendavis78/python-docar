import unittest
import json

from nose.tools import eq_, ok_
from mock import patch, Mock
from requests.auth import HTTPBasicAuth

from docar.backends import BackendManager, DjangoBackendManager, \
    HttpBackendManager
from docar import Document, Collection, fields


class when_a_backend_manager_gets_instantiated(unittest.TestCase):
    def it_can_provide_a_link_using_the_django_model(self):
        mock_model = Mock()
        mock_model.get_absolute_url.return_value = "link"

        manager = BackendManager('django')
        manager.instance = mock_model

        eq_("link", manager.uri())
        eq_(True, mock_model.get_absolute_url.called)

    def it_takes_the_backend_type_as_an_argument(self):
        manager = BackendManager('django')
        eq_('django', manager.backend_type)

    def it_defaults_to_the_django_backend_type(self):
        manager = BackendManager()
        eq_('django', manager.backend_type)

    def it_abstracts_a_specific_backend_manager(self):
        manager = BackendManager('django')
        ok_(isinstance(manager, DjangoBackendManager))

        manager = BackendManager('http')
        ok_(isinstance(manager, HttpBackendManager))

    def it_can_specify_the_backend_type_as_a_meta_option(self):
        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'django'
                model = Mock()

        doc = Doc()
        ok_(isinstance(doc._backend_manager, DjangoBackendManager))

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

        doc = Doc()
        ok_(isinstance(doc._backend_manager, HttpBackendManager))


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
    def it_can_take_credentials_as_argument(self, mock_auth):
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

        class OtherCol(Collection):
            document = Other

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()
            pub = fields.BooleanField()
            ext = fields.ForeignDocument(Other)
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

        expected = {
                'id': 1,
                'name': 'hello',
                'pub': True,
                'ext': {
                    'other': 'document'
                    },
                'col': [
                    {'other': 'first'},
                    {'other': 'second'},
                    ],
                'fetch': 'jaja'
                }
        response = Mock(name='mock_http_response')
        response.content = json.dumps(expected)
        response.status_code = 200

        # set the return value of the GET request
        self.mock_request.get.return_value = response

        # Make sure the name is not set right now
        eq_(expected['id'], doc.id)
        eq_(None, doc.name)

        # fetch the document from the HTTP backen, (is_bound = True)
        doc.fetch()

        eq_(expected['id'], doc.id)
        eq_(expected['name'], doc.name)
        eq_(expected['pub'], doc.pub)
        eq_(expected['fetch'], doc.fetched)
        eq_(None, doc.optional)
        eq_(True, isinstance(doc.ext, Other))
        eq_(True, isinstance(doc.col, OtherCol))

        # we should have made one GET request
        eq_([('get', {'url': 'http://location'})],
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


class when_a_django_backend_manager_gets_instantiated(unittest.TestCase):
    def it_can_fetch_save_and_delete_to_the_specific_backend_manager(self):
        with patch('docar.backends.DjangoBackendManager') as mock:
            mock_manager = Mock()
            mock_manager = mock.return_value
            manager = BackendManager('django')
            # first assert that the manager is really mocked
            ok_(isinstance(manager, Mock))
            manager.fetch()
            manager.save()
            manager.delete()
            eq_(True, mock_manager.fetch.called)
            eq_(True, mock_manager.save.called)
            eq_(True, mock_manager.delete.called)

    def it_returns_a_dict_representation_of_the_instance(self):
        Doc2Model = Mock(name="Doc2Model")
        mock_doc2_model = Mock(name="mock_model_instance",
                spec_set=['name', 'choice', 'related', 'coll', 'nonexistent',
                    'overwrite', 'overwritten'])
        mock_related = Mock()
        mock_related.name = 'related name'
        mock_m2m = Mock(name="mock_m2m")
        # return an empty list to have an iterator
        mock_m2m.all.return_value = []

        mock_doc2_model.name = "value"
        mock_doc2_model.choice = "True"
        mock_doc2_model.related = mock_related
        mock_doc2_model.coll = mock_m2m
        # the following instance field will be ingored but the to_dict method.
        mock_doc2_model.nonexistent = "whatever"
        # The following field will get overwritten
        mock_doc2_model.overwritten = 'jaja'

        Doc2Model.objects.get.return_value = mock_doc2_model

        Doc = Mock(spec_set=Document)
        Doc._meta.identifier = ['name']
        Coll = Mock(spec="Collection")

        class Doc2(Document):
            name = fields.StringField()
            choice = fields.BooleanField()
            related = fields.ForeignDocument(Doc)
            coll = fields.CollectionField(Coll)
            skipped = fields.NumberField()
            overwrite = fields.StringField()

            class Meta:
                model = Doc2Model
                identifier = 'name'

            def map_overwrite_field(self):
                return 'overwritten'

        mock_doc = Mock(spec_set=Document)
        mock_doc._meta = Mock()
        mock_doc._meta.identifier = []
        mock_coll = Mock(name="Collection")
        mock_doc = Doc.return_value
        mock_coll = Coll.return_value

        expected = {
                'name': 'value',
                'choice': 'True',
                'related': mock_doc,
                'coll': mock_coll,
                'skipped': None,
                'overwrite': 'jaja'
                }
        doc = Doc2({'name': 'value'})
        doc._backend_manager.instance = mock_doc2_model

        eq_(expected, doc._backend_manager._to_dict(doc))

    def it_can_fetch_data_from_the_underlying_model(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        mock_model.id = 1
        DjangoModel.objects.get.return_value = mock_model

        manager = BackendManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        doc = Mock(name="mock_document", spec=Document)
        field = fields.NumberField()
        field.name = "id"
        doc.id = 1
        doc._context = {}
        doc._get_context.return_value = {}
        doc._meta.identifier = ["id"]
        doc._identifier_state.return_value = {"id": 1}
        doc._prepare_save.return_value = {"id": 1}
        doc._meta.local_fields = [field]

        # make sure we are working with correct expectations
        eq_(DjangoBackendManager, type(manager))
        eq_({'id': 1}, manager.fetch(doc))
        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)

    def it_can_save_data_to_the_underlying_model(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        DjangoModel.objects.get_or_create.return_value = (mock_model, False)

        manager = BackendManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoBackendManager, type(manager))

        doc = Mock(name="mock_document", spec=Document)
        field = fields.NumberField()
        field.name = "id"
        doc.id = 1
        doc._context = {}
        doc._get_context.return_value = {}
        doc._meta.identifier = ["id"]
        doc._identifier_state.return_value = {"id": 1}
        doc._prepare_save.return_value = {"id": 1}
        doc._meta.local_fields = [field]

        # the manager.save() method doesn't return on success
        manager.save(doc)
        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)

    def it_can_delete_the_underlying_model_instance(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        mock_model.id = 1
        DjangoModel.objects.get.return_value = mock_model

        manager = BackendManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoBackendManager, type(manager))

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                model = DjangoModel

        doc = Doc({'id': 1})

        manager.delete(doc)

        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)
        eq_([('delete',)], mock_model.method_calls)

        # If the model does not exist, nothing happens
        DjangoModel.reset_mock()
        mock_model.reset_mock()

        DjangoModel.DoesNotExist = Exception
        DjangoModel.objects.get.side_effect = DjangoModel.DoesNotExist

        manager.delete(doc)

        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)
        # no method of the model should have been called
        eq_([], mock_model.method_calls)

    def it_can_return_a_django_m2m_relationship_as_collection(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        mock_model.id = 1
        mock_model.get_absolute_url.return_value = "A"

        OtherModel = Mock(name="OtherMock")
        mock1 = Mock()
        mock1.id = 1
        mock1.get_absolute_url.return_value = "1"
        mock2 = Mock()
        mock2.id = 2
        mock2.get_absolute_url.return_value = "2"

        # This mocks a many2many relation ship, its not a queryset, just a list
        mock_model.others.all.return_value = [mock1, mock2]

        x = [mock2, mock1]

        def mock_side_effect(*args, **kwargs):
            return x.pop()

        OtherModel.objects.get.side_effect = mock_side_effect
        DjangoModel.objects.get.return_value = mock_model

        # Now create a simple document setup
        class OtherDoc(Document):
            id = fields.NumberField()

            class Meta:
                identifier = 'id'
                model = OtherModel

        OtherCollection = Mock()
        OtherCollection.document = OtherDoc
        mock_col = OtherCollection.return_value
        mock_col.document = OtherDoc

        class Doc(Document):
            id = fields.NumberField()
            others = fields.CollectionField(OtherCollection)

            class Meta:
                identifier = 'id'
                model = DjangoModel

        manager = BackendManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoBackendManager, type(manager))

        doc = Doc({'id': 1})
        #doc.fetch()

        expected = {
                'id': 1,
                'others': mock_col}
        eq_(expected, manager.fetch(doc))

    def it_saves_collections_as_m2m_relations(self):
        # prepare the app structure
        Doc1Model = Mock(name="doc1_model")

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                model = Doc1Model

        class Doc1Col(Collection):
            document = Doc1

        Doc2Model = Mock(name="doc2_model")

        class Doc2(Document):
            id = fields.NumberField()
            # The bool field tests an edge case where boolean fields with a
            # default value of False are ignored unfortunately
            bool = fields.BooleanField(default=False)
            col = fields.CollectionField(Doc1Col)

            class Meta:
                model = Doc2Model

        request = {
                "id": 1,
                "col": [
                    {"id": 1},
                    {"id": 2}
                    ]
                }

        # now mock the underlying model store
        mock_doc2 = Mock(name="mock_doc2_model")
        mock_doc1_1 = Mock(name="mock_doc1_1")
        mock_doc1_2 = Mock(name="mock_doc1_2")

        Doc2Model.objects.get.return_value = mock_doc2

        collection_model = [mock_doc1_2, mock_doc1_1]

        def se(*args, **kwargs):
            return collection_model.pop()

        mock_doc2.col = Mock()
        mock_doc2.col.__dict__['model'] = Doc1Model
        mock_doc2.col.get.side_effect = se
        mock_doc2.col.get.return_value = True

        doc = Doc2(request)

        eq_(2, len(doc.col.collection_set))

        doc.save()

        eq_(True, mock_doc2.col.get.called)
        eq_(True, Doc2Model.objects.get.called)
        Doc2Model.objects.get.assert_called_once_with(id=1)

    def it_supplies_the_foreign_model_instance_when_saving_a_foreign_key(self):
        # prepare the app structure
        Doc1Model = Mock(name="doc1_model")

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                model = Doc1Model

        Doc2Model = Mock(name="doc2_model")

        class Doc2(Document):
            id = fields.NumberField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                model = Doc2Model

        # First return an existing model instance
        mock_doc1 = Mock()
        mock_doc2 = Mock()
        Doc1Model.objects.get.return_value = mock_doc1
        Doc2Model.objects.get_or_create.return_value = (mock_doc2, True)

        request = {
                "id": 1,
                "doc1": {
                    "id": 1
                    }
                }

        doc = Doc2(request)
        doc.save()

        ok_(isinstance(doc.doc1, Document))
        eq_(True, Doc1Model.objects.get.called)

        # Now save a non existing model
        mock_doc1.reset_mock()
        mock_doc2.reset_mock()
        Doc1Model.DoesNotExist = Exception
        Doc1Model.objects.get.side_effect = Doc1Model.DoesNotExist
        Doc1Model.objects.get_or_create.return_value = (mock_doc1, True)
        Doc2Model.objects.get_or_create.return_value = (mock_doc2, True)

        request = {
                "id": 1,
                "doc1": {
                    "id": 1
                    }
                }

        doc = Doc2(request)
        doc.save()

        ok_(isinstance(doc.doc1, Document))
        eq_(True, Doc1Model.objects.get.called)

    def it_applies_the_context_to_itself_and_its_foreign_documents(self):
        # prepare the app structure
        Doc1Model = Mock(name="doc1_model")
        Doc1Model.DoesNotExist = Exception

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                model = Doc1Model
                context = ['name']

        Doc2Model = Mock(name="doc2_model")

        class Doc2(Document):
            id = fields.NumberField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                model = Doc2Model
                context = ['name']

        # First return an existing model instance
        mock_doc1 = Mock()
        mock_doc2 = Mock()
        # The fetch for the foreign document will raise a BackendDoesNotExist
        # and therefore creates a new model instance
        Doc1Model.objects.get.side_effect = Doc1Model.DoesNotExist
        Doc1Model.objects.get.return_value = mock_doc1
        Doc2Model.objects.get.return_value = mock_doc2

        request = {
                "id": 2,
                "doc1": {
                    "id": 1
                    }
                }

        context = {'name': 'hello'}

        doc = Doc2(request, context=context)
        doc.save()

        #eq_([('objects.get', {'id': 1, 'name': 'hello'}),
        #    ('objects.get', {'id': 1, 'name': 'hello'})
        #    ], Doc1Model.method_calls)
        eq_([('objects.get', {'id': 1, 'name': 'hello'}),
            ], Doc1Model.method_calls)
        Doc2Model.objects.get.assert_called_once_with(id=2,
                name='hello')

    def it_can_save_nested_collections_on_the_django_backend(self):
        # Prepare an environment where you have a collection nesting another
        # collection
        Doc1Model = Mock(name="DjangoModel1")

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                model = Doc1Model

        class Doc1Collection(Collection):
            document = Doc1

        Doc2Model = Mock(name="DjangoModel2")

        class Doc2(Document):
            id = fields.NumberField()
            name = fields.StringField()
            doc1 = fields.CollectionField(Doc1Collection)

            class Meta:
                model = Doc2Model

            def map_doc1_field(self):
                return "doc1_map"

        class Doc2Collection(Collection):
            document = Doc2

        Doc3Model = Mock(name="DjangoModel3")

        class Doc3(Document):
            id = fields.NumberField()
            doc2 = fields.CollectionField(Doc2Collection)

            class Meta:
                model = Doc3Model

        post_data = {
                'id': 1,
                'doc2': [{
                        'id': 2,
                        'name': 'miss kitty',
                        'doc1': [
                            {'id': 3},
                            ]
                        }]
                }

        # create the document structure
        doc3 = Doc3(post_data)

        # and verify some expectations
        ok_(isinstance(doc3.doc2, Doc2Collection))
        eq_(1, len(doc3.doc2.collection_set))
        ok_(isinstance(doc3.doc2.collection_set[0], Doc2))
        temp_doc = doc3.doc2.collection_set[0]
        eq_('miss kitty', temp_doc.name)
        ok_(isinstance(temp_doc.doc1, Doc1Collection))

        # Now mock the django backend properly
        Doc1Model.DoesNotExist = Exception
        Doc2Model.DoesNotExist = Exception
        Doc3Model.DoesNotExist = Exception

        Doc3Model.objects.get.side_effect = Doc3Model.DoesNotExist
        mock_doc3 = Mock(name="Doc3")
        mock_doc3.id = 1
        mock_doc3.doc2 = Mock()
        mock_doc3.doc2.__dict__['model'] = Doc2Model
        Doc3Model.return_value = mock_doc3
        mock_doc2 = Mock()
        mock_doc2.__dict__['model'] = Doc2Model
        mock_doc2.id = 2
        mock_doc2.doc1_map = Mock(name='doc1_map')
        mock_doc2.doc1_map.__dict__['model'] = Doc1Model
        mock_doc3.doc2.create.return_value = mock_doc2
        mock_doc3.doc2.get.return_value = mock_doc2
        mock_doc1 = Mock()
        mock_doc1.__dict__['model'] = Doc1Model
        mock_doc1.id = 3
        mock_doc2.doc1_map.get.return_value = mock_doc1
        mock_doc2.doc1_map.create.return_value = mock_doc1

        # saving the model should create all nested relations too
        doc3.save()

        # make sure the right methods have been called.
        ok_(mock_doc2.doc1_map.get.called)
        ok_(mock_doc3.doc2.get.called)
        ok_(Doc3Model.called)

    def it_calls_the_fetch_field_method_when_saving(self):
        DocModel = Mock()

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                model = DocModel

            def map_name_field(self):
                return "mapped_name"

        # prepare the django backend
        DocModel.DoesNotExist = Exception
        DocModel.objects.get.side_effect = DocModel.DoesNotExist
        mock_doc = Mock()
        DocModel.return_value = mock_doc

        # create and save the document
        doc = Doc({'id': 1, 'name': 'docname'})

        manager = BackendManager()
        manager._model = DocModel
        manager.save(doc)

        # The save should have set this attribute on the django model as
        # defined by the map_field method
        eq_(True, hasattr(mock_doc, 'mapped_name'))
        # and also have the attribute set to the right value
        eq_('docname', mock_doc.mapped_name)

    def it_can_limit_the_choice_of_context_variables_given_to_it(self):
        Model1 = Mock()
        Model2 = Mock()

        class Doc1(Document):
            id = fields.NumberField()
            name1 = fields.StringField()

            class Meta:
                model = Model1
                context = ['name1']

        class Doc2(Document):
            id = fields.NumberField()
            name1 = fields.StringField()
            name2 = fields.StringField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                model = Model2
                context = ['name1', 'name2']

        # First return an existing model instance
        mock_doc1 = Mock()
        mock_doc1.id = 1
        mock_doc1.name1 = "name1"

        mock_doc2 = Mock()
        mock_doc2.id = 2
        mock_doc2.name1 = "name1"
        mock_doc2.name2 = "name2"
        mock_doc2.doc1 = mock_doc1

        # The fetch for the foreign document will raise a BackendDoesNotExist
        # and therefore creates a new model instance
        Model1.objects.get.return_value = mock_doc1
        Model2.objects.get.return_value = mock_doc2

        doc2 = Doc2({'id': 1}, context={'name1': 'name1', 'name2': 'name2'})
        doc2.fetch()
        doc2.save()

        Model1.objects.get.assert_called_with(id=1, name1="name1")
        Model2.objects.get.assert_called_with(id=2, name1="name1",
                name2="name2")
