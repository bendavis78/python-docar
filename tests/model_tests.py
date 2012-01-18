import unittest
import json

from nose.tools import eq_, ok_
from mock import patch, Mock

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

        class OtherCol(Collection):
            document = Other

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()
            pub = fields.BooleanField()
            ext = fields.ForeignDocument(Other)
            col = fields.CollectionField(OtherCol)

            class Meta:
                backend_type = 'http'

            def uri(self):
                return 'http://location'

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
                    ]
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
        eq_(True, isinstance(doc.ext, Other))
        eq_(True, isinstance(doc.col, OtherCol))


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

    def it_can_fetch_data_from_the_underlying_model(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
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
        doc._meta.identifier = ["id"]
        doc._identifier_state.return_value = {"id": 1}
        doc._save_state.return_value = {"id": 1}
        doc._meta.local_fields = [field]

        # make sure we are working with correct expectations
        eq_(DjangoBackendManager, type(manager))
        eq_(mock_model, manager.fetch(doc))
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
        doc._meta.identifier = ["id"]
        doc._identifier_state.return_value = {"id": 1}
        doc._save_state.return_value = {"id": 1}
        doc._meta.local_fields = [field]

        # the manager.save() method doesn't return on success
        manager.save(doc)
        eq_([('objects.get_or_create', {'id': 1})], DjangoModel.method_calls)

    def it_can_delete_the_underlying_model_instance(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        DjangoModel.objects.get.return_value = mock_model

        manager = BackendManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoBackendManager, type(manager))

        # mock the actual document
        doc = Mock(name="MockDoc", spec=Document)
        doc._identifier_state.return_value = {"id": 1}

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

        DjangoModel.objects.get.return_value = mock_model

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

        # Now create a simple document setup
        class OtherDoc(Document):
            id = fields.NumberField()

            class Meta:
                identifier = 'id'
                model = OtherModel

        class OtherCollection(Collection):
            document = OtherDoc

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

        doc = Doc()
        doc.fetch()

        expected = {
                "id": 1,
                "link": {
                    "rel": "self",
                    "href": "A"
                    },
                "others": [
            {
            "rel": "item",
            "href": "1",
            "id": 1
            },
            {
            "rel": "item",
            "href": "2",
            "id": 2
            }
        ]}

        eq_(expected, doc._prepare_render())

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

        Doc2Model.objects.get_or_create.return_value = (mock_doc2, False)

        collection_model = [(mock_doc1_2,), (mock_doc1_1,)]

        def se(*args, **kwargs):
            return collection_model.pop()

        mock_doc2.col = Mock()
        mock_doc2.col.get_or_create.side_effect = se

        doc = Doc2(request)

        eq_(2, len(doc.col.collection_set))

        doc.save()

        eq_(True, mock_doc2.col.get_or_create.called)
        eq_(True, Doc2Model.objects.get_or_create.called)
        Doc2Model.objects.get_or_create.assert_called_once_with(id=1,
                bool=False)

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

        Doc2Model = Mock(name="doc2_model")

        class Doc2(Document):
            id = fields.NumberField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                model = Doc2Model

        # First return an existing model instance
        mock_doc1 = Mock()
        mock_doc2 = Mock()
        # The fetch for the foreign document will raise a BackendDoesNotExist
        # and therefore creates a new model instance
        Doc1Model.objects.get.side_effect = Doc1Model.DoesNotExist
        Doc1Model.objects.get_or_create.return_value = (mock_doc1, True)
        Doc2Model.objects.get_or_create.return_value = (mock_doc2, True)

        request = {
                "id": 2,
                "doc1": {
                    "id": 1
                    }
                }

        context = {'name': 'hello'}

        doc = Doc2(request, context=context)
        doc.save()

        Doc1Model.objects.get_or_create.assert_called_once_with(id=1,
                name='hello')
        Doc2Model.objects.get_or_create.assert_called_once_with(id=2,
                name='hello', doc1=mock_doc1)
