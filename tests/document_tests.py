import unittest
import json

from nose.tools import eq_, assert_raises, ok_
from mock import Mock

from docar import documents
from docar import fields
from docar import Document, Collection
from docar.backends import DjangoBackendManager
from docar.exceptions import BackendDoesNotExist

from .app import Article
from .app import Editor


BASKET = {
        "is_rotten": True,
        "name": "Lovely Basket",
        "link": {
            "rel": "self",
            "href": "http://localhost/basket/1/"
            }
        }

FRUIT_CHOICES = (
        (0, 'sweet'),
        (1, 'sour')
        )


class LemonFruit(documents.Document):
    #taste = fields.ChoiceField(choices=FRUIT_CHOICES)
    count = fields.NumberField(default=1)


class FruitBasket(documents.Document):
    is_rotten = fields.BooleanField(default=False)
    name = fields.StringField()

    class Meta:
        model = 'haha'

    def uri(self):
        return "http://localhost/basket/1/"


class SpecialFruitBasket(FruitBasket):
    is_present = fields.BooleanField()
    #lemons = fields.CollectionField(LemonFruit)


class when_a_document_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.basket = FruitBasket()
        self.article = Article()

    def it_has_a_to_json_method(self):
        eq_(True, hasattr(self.article, 'to_json'))

    def it_has_a_save_method(self):
        eq_(True, hasattr(self.article, 'save'))

    def it_has_a_fetch_method(self):
        eq_(True, hasattr(self.article, 'fetch'))

    def it_has_a_delete_method(self):
        eq_(True, hasattr(self.article, 'delete'))

    def it_has_a_list_of_fields_in_meta(self):
        eq_(list, type(self.article._meta.local_fields))
        eq_(fields.NumberField, type(self.article._meta.local_fields[0]))
        eq_(fields.StringField, type(self.article._meta.local_fields[1]))

    def it_stores_seperates_lists_for_the_different_types_of_fields(self):
        """The document _meta attribute stores different lists for the
        different types of fields. So that later when saving to the model it
        can treat them differently."""
        Model = Mock()
        Col = Mock(name="collection", spec=Collection)
        Relation = Mock(name="relation", spec="Document")

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()
            foreign = fields.ForeignDocument(Relation)
            collection = fields.CollectionField(Col)

            class Meta:
                model = Model

        d = Doc()

        eq_(list, type(d._meta.local_fields))
        eq_(list, type(d._meta.related_fields))
        eq_(list, type(d._meta.collection_fields))

        eq_(1, len(d._meta.related_fields))
        eq_(1, len(d._meta.collection_fields))
        eq_(4, len(d._meta.local_fields))

    def it_has_an_attribute_for_each_field(self):
        eq_(True, hasattr(self.article, 'name'))
        eq_(None, self.article.name)

        # If a default value is specified, the field is set to that one
        eq_(True, hasattr(self.article, 'id'))
        eq_(None, self.article.id)

    def it_has_a_meta_attribute_to_store_options(self):
        eq_(True, hasattr(self.article, '_meta'))

    def it_has_many_options_initialized_with_default_values(self):
        eq_(True, hasattr(self.article._meta, 'excludes'))
        eq_([], self.article._meta.excludes)
        eq_(True, hasattr(self.article._meta, 'identifier'))
        eq_(['id'], self.article._meta.identifier)

    def it_converts_string_identifiers_to_a_list_of_identifiers(self):
        class Doc(Document):
            name = fields.StringField()
            age = fields.NumberField()

            class Meta:
                identifier = 'name'

        class Doc2(Document):
            name = fields.StringField()
            age = fields.NumberField()

            class Meta:
                identifier = ['name', 'age']

        d = Doc()
        eq_(['name'], d._meta.identifier)

        d = Doc2()
        eq_(['name', 'age'], d._meta.identifier)

    def it_can_determine_the_right_model_using_defined_identifiers(self):
        # Prepare a valid editor resource
        editor = Editor({
            'first_name': 'Christo',
            'last_name': 'Buschek'})
        mock_editor = {
                'first_name': 'Christo',
                'last_name': 'Buschek',
                'age': 31}
        #mock_editor = EditorModel.return_value
        #mock_editor.first_name = "Christo"
        #mock_editor.last_name = "Buschek"
        #mock_editor.age = 31

        editor._backend_manager = Mock()
        editor._backend_manager.fetch.return_value = mock_editor

        # the editor should fetch the age correctly
        editor.fetch()
        eq_(31, editor.age)

    def it_stores_the_declared_fields_in_the_right_order(self):
        special = SpecialFruitBasket()

        # expect the fields to be stored in this order
        eq_('is_rotten', special._meta.local_fields[0].name)
        eq_('name', special._meta.local_fields[1].name)
        eq_('is_present', special._meta.local_fields[2].name)

    def it_saves_the_field_attribute_name_inside_the_field(self):
        eq_('is_rotten', self.basket._meta.local_fields[0].name)
        eq_('name', self.basket._meta.local_fields[1].name)

    def it_can_extract_the_identifier_state_from_itself(self):
        Model = Mock()

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                model = Model

        expected = {"id": 1}

        doc = Doc({"id": 1, "name": "name"})

        eq_(expected, doc._identifier_state())

    def it_can_provide_a_overwrite_field_for_its_state_processing(self):
        Model = Mock()

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                model = Model

            def render_name_field(self):
                return "render_field"

            def save_name_field(self):
                return "save_field"

            def map_name_field(self):
                return "map_field"

            def uri(self):
                # specify this function, otherwise we have to make a more
                # complicated mocked model
                return "http://location"

        expected = {"id": 1, "name": "render_field", "link":
                {"rel": "self", "href": "http://location"}
                }

        doc = Doc({"id": 1, "name": "name"})

        eq_("name", doc.name)
        eq_(expected, doc.to_python())

        expected['name'] = "save_field"
        del(expected['link'])
        eq_(expected, doc._prepare_save())

        expected['name'] = "map_field"
        eq_(expected, doc._prepare_fetch())

    def it_can_fetch_its_state_from_the_model_backend(self):
        doc1 = Article({'id': 1})

        # mock the model manager return
        mock_doc1 = {'id': 1}
        doc1._backend_manager = Mock()
        doc1._backend_manager.fetch.return_value = mock_doc1

        # before we actually fetch the document, name should be empty
        eq_(None, doc1.name)

        # we change the name attribute of the model instance
        mock_doc1['name'] = "hello"

        # this should all work out now
        doc1.fetch()
        eq_("hello", doc1.name)

        # mock the manager object, It should throw an exception
        doc1._backend_manager.fetch.side_effect = BackendDoesNotExist

        assert_raises(BackendDoesNotExist, doc1.fetch)

    def it_creates_a_backend_manager(self):
        doc1 = Article({'id': 1})

        eq_(True, hasattr(doc1, '_backend_manager'))
        eq_(DjangoBackendManager, type(doc1._backend_manager))

    def it_doesnt_render_optional_fields_that_are_set_to_none(self):
        DocModel = Mock(name='DocModel')

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField(optional=True)

            class Meta:
                model = DocModel

        mock_doc = {'id': 1, 'name': None}

        expected = {'id': 1, 'link': {
            'rel': 'self',
            'href': 'link'}}
        doc = Doc({'id': 1})

        doc._backend_manager = Mock()
        doc._backend_manager.uri.return_value = "link"
        doc._backend_manager.fetch.return_value = mock_doc

        doc.fetch()

        # name is not set, so don't render it
        eq_(expected, json.loads(doc.to_json()))

        # now set name and make sure it gets rendered
        mock_doc['name'] = 'hello'
        expected['name'] = "hello"

        doc.fetch()
        eq_(expected, json.loads(doc.to_json()))

    def it_doesnt_render_fields_with_render_option_set_to_false(self):
        DocModel = Mock(name='DocModel')

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField(render=False)

            class Meta:
                model = DocModel

        mock_doc = {'id': 1, 'name': 'name'}

        expected = {'id': 1, 'link': {
            'rel': 'self',
            'href': 'link'}}
        doc = Doc({'id': 1})

        doc._backend_manager = Mock()
        doc._backend_manager.uri.return_value = "link"
        doc._backend_manager.fetch.return_value = mock_doc

        doc.fetch()

        # name is set not to render, so don't render it
        eq_(expected, json.loads(doc.to_json()))

    def it_can_supply_extra_context_also_to_its_foreign_documents(self):
        Model1 = Mock()
        Model2 = Mock()

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                model = Model1

        class Doc2(Document):
            id = fields.NumberField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                model = Model2

        context = {'name': 'hello'}

        doc2 = Doc2({'id': 1, 'doc1': {'id': 2}}, context=context)

        eq_(context, doc2._context)
        eq_(context, doc2.doc1._context)

    def it_can_supply_additional_parameters_to_the_backend_manager(self):
        mock_manager = Mock(name="mocked_http_backend_manager")
        mock_manager.fetch.return_value = {}

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

        doc = Doc1({'id': 1})
        doc._backend_manager = mock_manager

        # simulate a fetch
        doc.fetch(username='crito', password='secret')

        eq_([('fetch', (doc,), {'username': 'crito', 'password': 'secret'})],
                mock_manager.method_calls)

    def it_gives_context_based_on_the_meta_options(self):
        Model1 = Mock()
        Model2 = Mock()

        class Doc1(Document):
            id = fields.NumberField()

            class Meta:
                model = Model1
                context = ['name']

        class Doc2(Document):
            id = fields.NumberField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                model = Model2
                context = ['name', 'other']

        doc2 = Doc2({'id': 1, 'doc1': {'id': 2}},
                context={'name': 'name', 'other': 'other'})

        eq_({'name': 'name', 'other': 'other'}, doc2._get_context())
        eq_({'name': 'name'}, doc2.doc1._get_context())

    def it_can_be_scaffolded(self):
        Model1 = Mock(name="MockModel1")
        Model2 = Mock(name="MockModel2")

        class Doc1(Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                model = Model1

        class Col(Collection):
            document = Doc1

        class Doc2(Document):
            id = fields.NumberField()
            name = fields.StringField()
            doc1 = fields.ForeignDocument(Doc1)
            col1 = fields.CollectionField(Col)
            col2 = fields.CollectionField(Col)
            opt = fields.NumberField(optional=True)
            bool1 = fields.BooleanField(default=True)
            bool2 = fields.BooleanField()
            xx = fields.StaticField(value="Static")
            noscaffold = fields.NumberField(scaffold=False)

            class Meta:
                model = Model2

        expected = {
                "id": None,
                "name": "",
                "bool1": True,
                "bool2": None,
                "doc1": {
                    "id": 1,
                    "name": "Hello Universe"},
                "col1": [
                    {"id": 2, "name": ""},
                    {"id": None, "name": ""}
                    ],
                "col2": []
                }

        doc2 = Doc2()
        doc2.doc1.id = 1
        doc2.doc1.name = "Hello Universe"
        d1 = Doc1()
        d2 = Doc1()

        d1.id = 2
        doc2.col1.add(d1)
        doc2.col1.add(d2)

        eq_(expected, doc2.scaffold())


class when_a_representation_is_parsed(unittest.TestCase):
    def setUp(self):
        self.basket = FruitBasket(BASKET)

    def it_has_the_fields_bound(self):
        eq_(True, self.basket.is_rotten)
        eq_('Lovely Basket', self.basket.name)


class when_a_document_inherits_from_another_document(unittest.TestCase):
    def setUp(self):
        self.basket = SpecialFruitBasket()

    def it_doesnt_overrides_meta_options_of_the_parent(self):
        class BaseDocument(Document):
            class Meta:
                identifier = 'name'
                excludes = ['id']

        doc = BaseDocument()
        eq_(['id'], doc._meta.excludes)
        eq_(['name'], doc._meta.identifier)

        class ChildDocument(BaseDocument):
            class Meta(BaseDocument.Meta):
                excludes = ['id', 'key']

        doc = ChildDocument()
        eq_(['id', 'key'], doc._meta.excludes)
        eq_(['id'], doc._meta.identifier)

    def it_inherits_all_fields(self):
        # that should be the total amount of fields for the inherited document
        eq_(3, len(self.basket._meta.local_fields))
        #eq_(True, 'is_present' in self.basket.fields)
        #eq_(True, 'is_rotten' in self.basket.fields)
        #eq_(True, 'name' in self.basket.fields)


class when_a_document_is_bound(unittest.TestCase):
    def setUp(self):
        self.basket = FruitBasket()
        self.basket.name = 'Lovely Basket'
        self.basket.is_rotten = True

    def it_can_render_to_json(self):
        eq_(json.dumps(BASKET), self.basket.to_json())

    def it_can_be_rendered_to_a_python_dictionary(self):
        eq_(BASKET, self.basket.to_python())

    def it_can_collect_links(self):
        eq_('http://localhost/basket/1/', self.basket.uri())

    def it_can_be_saved_to_model(self):
        # Mock the actual django model
        DjangoModel = Mock(name='DjangoModel')

        class ModelDocument(documents.Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                # Use the mocked django model
                model = DjangoModel

        # create the mocked instance of the model
        mock_model = DjangoModel.return_value

        # mock the manager object, It should throw an exception
        DjangoModel.objects.get_or_create.return_value = (mock_model, False)

        # The expectation is that this instance gets newly created
        instance = ModelDocument({'id': 23, 'name': 'hello world'})
        instance._backend_manager.save = Mock()
        instance.save()

        eq_(True, instance._backend_manager.save.called)

    def it_can_delete_its_model_backend(self):
        doc1 = Article({'id': 1})

        # mock the model manager return
        mock_doc1 = Mock()
        mock_doc1.id = 1
        doc1._backend_manager = Mock()
        doc1._backend_manager.fetch.return_value = mock_doc1

        # delete the model
        doc1.delete()
        eq_([('delete', (doc1,))], doc1._backend_manager.method_calls)

    def it_can_update_the_underlying_model(self):
        # Mock the actual django model
        DjangoModel = Mock(name='DjangoModel')

        class ModelDocument(documents.Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                # Use the mocked django model
                model = DjangoModel

        # create the mocked instance of the model, backend_manager.fetch
        # returns it further down
        mock_model = {'id': 24, 'name': 'hello universe'}

        # The expectation is that this instance gets newly created
        instance = ModelDocument({'id': 24, 'name': 'hello universe'})
        instance._backend_manager = Mock()
        instance._backend_manager.fetch.return_value = mock_model
        instance.update({'name': 'new name'})

        eq_('new name', instance.name)
        eq_([
            ('fetch', (instance,)),
            ('save', (instance,))], instance._backend_manager.method_calls)


class when_a_document_contains_a_foreign_document_relation(unittest.TestCase):
    def it_can_render_the_document_inline(self):
        Doc1Model = Mock(name="doc1_model")
        Doc2Model = Mock(name="doc2_model")

        class Doc1(Document):
            name = fields.StringField()

            class Meta:
                model = Doc1Model
                identifier = 'name'

            def uri(self):
                return 'http://location'

        class Doc2(Document):
            name = fields.StringField()
            doc1 = fields.ForeignDocument(Doc1)

            class Meta:
                model = Doc2Model
                identifier = 'name'

            def uri(self):
                return 'http://location'

        doc1 = Doc1({'name': 'doc1'})
        doc2 = Doc2({'name': 'doc2'})
        doc2._backend_manager = Mock()
        doc2._backend_manager.fetch.return_value = {
                'name': 'doc2',
                'doc1': doc1}

        doc2.fetch()

        expected = {
                'name': 'doc2',
                'doc1': {
                    'rel': 'related',
                    'name': 'doc1',
                    'href': 'http://location'
                    },
                'link': {
                    'rel': 'self',
                    'href': 'http://location'}
                }

        eq_(expected, json.loads(doc2.to_json()))

    def it_sets_the_attribute_as_a_document(self):
        DjangoModel = Mock(name='DjangoModel')

        mock_model = Mock()
        mock_model.id = 34
        DjangoModel.objects.get.return_value = mock_model

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                model = DjangoModel

        OtherModel = Mock(name='OtherModel')

        class Other(Document):
            id = fields.NumberField()
            doc = fields.ForeignDocument(Doc)

            class Meta:
                model = OtherModel

        message = {
                "id": 1,
                "doc": {"id": 34}
                }

        doc = Other(message)
        ok_(isinstance(doc.doc, Doc))

    def it_ignores_optional_or_none_type_foreign_documents(self):
        DjangoModel = Mock()

        class Other(Document):
            id = fields.NumberField()

            class Meta:
                model = DjangoModel

        OtherModel = Mock(name='OtherModel')

        class Doc(Document):
            id = fields.NumberField()
            other = fields.ForeignDocument(Other, optional=True)

            class Meta:
                model = OtherModel

        doc = Doc({'id': 1})

        eq_(True, hasattr(doc._meta.local_fields[1], 'optional'))
        eq_(True, doc._meta.local_fields[1].optional)

        eq_({'id': 1}, doc._prepare_save())


class when_a_document_contains_a_collection_field(unittest.TestCase):
    def it_sets_the_collection_as_attribute_for_the_field(self):
        MockDoc = Mock()
        MockModel = Mock()

        class Col(Collection):
            document = MockDoc

        class Doc(Document):
            id = fields.NumberField()
            col = fields.CollectionField(Col)

            class Meta:
                model = MockModel

        doc = Doc()

        ok_(isinstance(doc.col, Col))

    def it_creates_a_bound_collection_upon_instantiation_of_the_document(self):
        MockModel = Mock()
        ColMockModel = Mock()

        class ColDoc(Document):
            id = fields.NumberField()

            class Meta:
                model = ColMockModel

        class Col(Collection):
            document = ColDoc

        class Doc(Document):
            id = fields.NumberField()
            col = fields.CollectionField(Col)

            class Meta:
                model = MockModel

        request = {
                "id": 1,
                "col": [
                    {"id": 2},
                    {"id": 3}
                    ]
                }

        doc = Doc(request)

        ok_(isinstance(doc.col, Col))
        eq_(2, len(doc.col.collection_set))
