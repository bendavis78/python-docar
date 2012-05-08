import unittest

from nose.tools import eq_, ok_
from mock import patch, Mock

from docar.backends import BackendManager, DjangoBackendManager
from docar import Document, Collection, fields


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

        class Doc(Document):
            name = fields.StringField()

            class Meta:
                backend_type = 'django'
                identifier = 'name'
                model = Mock()

        class Coll(Collection):
            document = Doc

        class Doc2(Document):
            name = fields.StringField()
            choice = fields.BooleanField()
            related = fields.ForeignDocument(Doc)
            coll = fields.CollectionField(Coll)
            skipped = fields.NumberField()
            overwrite = fields.StringField()

            class Meta:
                model = Doc2Model
                backend_type = 'django'
                identifier = 'name'

            def map_overwrite_field(self):
                return 'overwritten'

        expected = {
                'name': 'value',
                'choice': 'True',
                'related': {'name': 'related name'},
                'coll': [],
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
        doc._save.return_value = {"id": 1}
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
        doc._save.return_value = {"id": 1}
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
                backend_type = 'django'
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
                backend_type = 'django'
                identifier = 'id'
                model = OtherModel

        class OtherCollection(Collection):
            document = OtherDoc

        class Doc(Document):
            id = fields.NumberField()
            others = fields.CollectionField(OtherCollection)

            class Meta:
                backend_type = 'django'
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
                'others': [{'id': 1}, {'id': 2}]}
        eq_(expected, manager.fetch(doc))

    def it_saves_collections_as_m2m_relations(self):
        # prepare the app structure
        Doc1Model = Mock(name="doc1_model")

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'django'
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
                backend_type = 'django'
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

        # I have to mock a queryset for each collection, cause I run an exclude
        # on it everytime I iterate through an item of the collection
        qs_col = Mock(name="queryset")
        qs_col.__len__ = Mock(return_value=2)
        qs_col.__getitem__ = Mock()
        qs_col.__iter__ = Mock(
                return_value=iter([mock_doc1_1, mock_doc1_2]))

        qs_cola = Mock(name="queryset-exclude_cola")
        qs_cola.__len__ = Mock(return_value=1)
        qs_cola.__getitem__ = Mock()
        qs_cola.__iter__ = Mock(return_value=iter([mock_doc1_2]))

        qs_col.exclude.return_value = qs_cola
        qs_colb = Mock(name="queryset-exclude_colb")
        qs_colb.__len__ = Mock(return_value=1)
        qs_colb.__getitem__ = Mock()
        qs_colb.__iter__ = Mock(return_value=iter([]))
        qs_cola.exclude.return_value = qs_colb

        mock_doc2.col = Mock()
        mock_doc2.col.__dict__['model'] = Doc1Model
        mock_doc2.col.get.side_effect = se
        mock_doc2.col.get.return_value = True
        mock_doc2.col.all.return_value = qs_col

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
                backend_type = 'django'
                model = Doc1Model

        Doc2Model = Mock(name="doc2_model")

        class Doc2(Document):
            id = fields.NumberField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                backend_type = 'django'
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
                backend_type = 'django'
                model = Doc1Model
                context = ['name']

        Doc2Model = Mock(name="doc2_model")

        class Doc2(Document):
            id = fields.NumberField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                backend_type = 'django'
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

        eq_([('objects.get', {'id': 1, 'name': 'hello'}),
            ('objects.get', {'id': 1, 'name': 'hello'})
            ], Doc1Model.method_calls)
        #eq_([('objects.get', {'id': 1, 'name': 'hello'}),
        #    ], Doc1Model.method_calls)
        Doc2Model.objects.get.assert_called_once_with(id=2,
                name='hello')

    def it_can_save_nested_collections_on_the_django_backend(self):
        # Prepare an environment where you have a collection nesting another
        # collection
        Doc1Model = Mock(name="DjangoModel1")

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'django'
                model = Doc1Model

        class Doc1Collection(Collection):
            document = Doc1

        Doc2Model = Mock(name="DjangoModel2")

        class Doc2(Document):
            id = fields.NumberField()
            name = fields.StringField()
            doc1 = fields.CollectionField(Doc1Collection)

            class Meta:
                backend_type = 'django'
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
                backend_type = 'django'
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

        # I have to mock a queryset for each collection, cause I run an exclude
        # on it everytime I iterate through an item of the collection
        qs_doc2 = Mock(name="queryset2")
        qs_doc2.__len__ = Mock(return_value=1)
        qs_doc2.__getitem__ = Mock()
        qs_doc2.__iter__ = Mock(
                return_value=iter([mock_doc2]))
        qs_doc2a = Mock(name="queryset-exclude_doc2")
        qs_doc2a.__iter__ = Mock(return_value=iter([]))
        qs_doc2.exclude.return_value = qs_doc2a

        mock_doc3.doc2.all.return_value = qs_doc2
        mock_doc3.doc2.create.return_value = mock_doc2
        mock_doc3.doc2.get.return_value = mock_doc2
        mock_doc1 = Mock()
        mock_doc1.__dict__['model'] = Doc1Model
        mock_doc1.id = 3

        qs_doc1 = Mock(name="queryset1")
        qs_doc1.__len__ = Mock(return_value=1)
        qs_doc1.__getitem__ = Mock()
        qs_doc1.__iter__ = Mock(
                return_value=iter([mock_doc1]))

        qs_doc1a = Mock(name="queryset-exclude_doc1")
        qs_doc1a.__len__ = Mock(return_value=0)
        qs_doc1a.__getitem__ = Mock()
        qs_doc1a.__iter__ = Mock(return_value=iter([]))
        qs_doc1.exclude.return_value = qs_doc1a

        mock_doc2.doc1_map.all.return_value = qs_doc1
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
                backend_type = 'django'
                model = Model1
                context = ['name1']

        class Doc2(Document):
            id = fields.NumberField()
            name1 = fields.StringField()
            name2 = fields.StringField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                backend_type = 'django'
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

        #Model1.objects.get.assert_called_with(id=1, name1="name1")
        Model2.objects.get.assert_called_with(id=2, name1="name1",
                name2="name2")

    def it_can_delete_items_from_a_m2m_relation(self):
        Model1 = Mock()
        Model2 = Mock()

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'django'
                model = Model1

        class Col1(Collection):
            document = Doc1

        class Doc2(Document):
            id = fields.NumberField()
            col1 = fields.CollectionField(Col1)

            class Meta:
                backend_type = 'django'
                model = Model2

        # First return an existing model instance
        mock_doc1a = Mock()
        mock_doc1a.id = 1
        mock_doc1a.__dict__['model'] = Model1

        mock_doc1b = Mock()
        mock_doc1b.id = 2
        mock_doc1b.__dict__['model'] = Model1

        m2m_relation = Mock(name="m2m_relation")
        mock_doc2 = Mock()
        mock_doc2.col1 = m2m_relation
        mock_doc2.id = 3
        mock_doc2.col1.__dict__['model'] = Model1

        # The fetch for the foreign document will raise a BackendDoesNotExist
        # and therefore creates a new model instance
        Model2.objects.get.return_value = mock_doc2

        Queryset = Mock(name="queryset")
        Queryset.__len__ = Mock(return_value=2)
        Queryset.__getitem__ = Mock()
        Queryset.__iter__ = Mock(
                return_value=iter([mock_doc1a, mock_doc1b]))
        m2m_relation.all.return_value = Queryset

        doc = Doc2({'id': 1, 'col1':[]})
        doc.save()

        # If the collection is empty we make sure that the backend instances
        # are delete too
        eq_(True, mock_doc1a.delete.called)
        eq_(True, mock_doc1b.delete.called)

        mock_doc1a.reset_mock()
        mock_doc1b.reset_mock()
        m2m_relation.all.reset_mock()

        Queryset1 = Mock(name="queryset1")
        Queryset1.__len__ = Mock(return_value=2)
        Queryset1.__getitem__ = Mock()
        Queryset1.__iter__ = Mock(
                return_value=iter([mock_doc1a, mock_doc1b]))
        Queryset2 = Mock(name="queryset2")
        Queryset2.__len__ = Mock(return_value=1)
        Queryset2.__getitem__ = Mock()
        Queryset2.__iter__ = Mock(
                return_value=iter([mock_doc1b]))


        m2m_relation.all.return_value = Queryset1
        Queryset1.exclude.return_value = Queryset2

        doc = Doc2({'id': 1, 'col1':[{'id':1}]})
        doc.save()

        m2m_relation.get.assert_called_once_with(id=1)
        eq_(True, mock_doc1b.delete.called)

    def it_can_supply_context_to_foreign_documents_within_nested_collections(self):
        # FIXME: Add a test for this use case
        pass
