import unittest

from nose.tools import eq_, ok_
from mock import patch, Mock

from docar.models import ModelManager, DjangoModelManager
from docar import Document, Collection, fields


class when_a_model_manager_gets_instantiated(unittest.TestCase):
    def it_takes_the_model_type_as_an_argument(self):
        manager = ModelManager('django')
        eq_('django', manager.model_type)

    def it_defaults_to_the_django_model_type(self):
        manager = ModelManager()
        eq_('django', manager.model_type)

    def it_abstracts_a_specific_model_manager(self):
        manager = ModelManager('django')
        ok_(isinstance(manager, DjangoModelManager))

    def it_can_fetch_save_and_delete_to_the_specific_model_manager(self):
        with patch('docar.models.DjangoModelManager') as mock:
            mock_manager = Mock()
            mock_manager = mock.return_value
            manager = ModelManager('django')
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

        manager = ModelManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoModelManager, type(manager))
        eq_(mock_model, manager.fetch(id=1))
        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)

    def it_can_save_data_to_the_underlying_model(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        DjangoModel.objects.get.return_value = mock_model

        manager = ModelManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoModelManager, type(manager))

        doc = Mock(name="mock_document")
        field = Mock(name="mock_field")
        field.name = "id"
        doc.id = 1
        doc._meta.identifier = ["id"]
        doc._get_document_state.return_value = {"id": 1}
        doc._meta.local_fields = [field]

        # the manager.save() method doesn't return on success
        manager.save(doc)
        eq_([('objects.get_or_create', {'id': 1})], DjangoModel.method_calls)

    def it_can_delete_the_underlying_model_instance(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        DjangoModel.objects.get.return_value = mock_model

        manager = ModelManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoModelManager, type(manager))

        manager.delete(['id'], id=1)

        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)
        eq_([('delete',)], mock_model.method_calls)

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

        manager = ModelManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoModelManager, type(manager))

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

        eq_(expected, doc.to_attributes())

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
        mock_doc1 = Mock(name="mock_doc1_model")
        mock_doc2_1 = Mock(name="mock_doc2_1")
        mock_doc2_2 = Mock(name="mock_doc2_2")

        Doc1Model.objects.get_or_create.return_value = mock_doc1

        collection_model = [mock_doc2_2, mock_doc2_1]

        def se(*args, **kwargs):
            return collection_model.pop()

        Doc2Model.objects.get_or_create.side_effect = se

        doc = Doc1(request)
        doc.save()

        eq_(True, Doc1Model.objects.get_or_create.called)
        eq_(True, Doc2Model.objects.get_or_create.called)
