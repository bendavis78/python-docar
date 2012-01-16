import unittest
import types
import json

from nose.tools import eq_, assert_raises, ok_
from nose.exc import SkipTest
from mock import Mock

from docar import documents
from docar import fields
from docar import Document, Collection
from docar.models import DjangoModelManager
from docar.exceptions import ModelDoesNotExist

from app import Article, ArticleModel
from app import Editor, EditorModel
from app import TagModel


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
        eq_(types.ListType, type(self.article._meta.local_fields))
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

        eq_(types.ListType, type(d._meta.local_fields))
        eq_(types.ListType, type(d._meta.related_fields))
        eq_(types.ListType, type(d._meta.collection_fields))

        eq_(1, len(d._meta.related_fields))
        eq_(1, len(d._meta.collection_fields))
        eq_(4, len(d._meta.local_fields))

    def it_has_an_attribute_for_each_field(self):
        eq_(True, hasattr(self.article, 'name'))
        eq_(types.NoneType, type(self.article.name))

        # If a default value is specified, the field is set to that one
        eq_(True, hasattr(self.article, 'id'))
        eq_(types.NoneType, type(self.article.id))

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
        mock_editor = EditorModel.return_value
        mock_editor.first_name = "Christo"
        mock_editor.last_name = "Buschek"
        mock_editor.age = 31

        mock_editor._model_manager = Mock()
        mock_editor._model_manager.fetch.return_value = mock_editor

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

    def it_can_provide_a_render_field_for_a_field(self):
        Model = Mock()

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                model = Model

            def render_name_field(self):
                return "something"

            def uri(self):
                # specify this function, otherwise we have to make a more
                # complicated mocked model
                return "http://location"

        expected = {"id": 1, "name": "something", "link":
                {"rel": "self", "href": "http://location"}
                }

        doc = Doc({"id": 1, "name": "name"})

        eq_("name", doc.name)
        eq_(expected, doc._prepare_render())

    def it_can_fetch_its_state_from_the_model_backend(self):
        doc1 = Article({'id': 1})

        # mock the model manager return
        mock_doc1 = Mock()
        mock_doc1.id = 1
        doc1._model_manager = Mock()
        doc1._model_manager.fetch.return_value = mock_doc1

        # before we actually fetch the document, name should be empty
        eq_(None, doc1.name)

        # we change the name attribute of the model instance
        mock_doc1.name = "hello"

        # this should all work out now
        doc1.fetch()
        eq_("hello", doc1.name)

        # mock the manager object, It should throw an exception
        doc1._model_manager.fetch.side_effect = ModelDoesNotExist

        assert_raises(ModelDoesNotExist, doc1.fetch)

    def it_creates_a_model_manager(self):
        doc1 = Article({'id': 1})

        eq_(True, hasattr(doc1, '_model_manager'))
        eq_(DjangoModelManager, type(doc1._model_manager))

    def it_doesnt_render_optional_fields_that_are_set_to_none(self):
        DocModel = Mock(name='DocModel')

        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField(optional=True)

            class Meta:
                model = DocModel

        mock_doc = Mock()
        mock_doc.id = 1
        mock_doc.name = None

        expected = {'id': 1, 'link': {
            'rel': 'self',
            'href': 'link'}}
        doc = Doc({'id': 1})

        doc._model_manager = Mock()
        doc._model_manager.uri.return_value = "link"
        doc._model_manager.fetch.return_value = mock_doc

        doc.fetch()

        # name is not set, so don't render it
        eq_(expected, json.loads(doc.to_json()))

        # now set name and make sure it gets rendered
        mock_doc.name = 'hello'
        expected['name'] = "hello"

        doc.fetch()
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
        eq_(BASKET, self.basket._prepare_render())

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
        instance._model_manager.save = Mock()
        instance.save()

        eq_(True, instance._model_manager.save.called)

    def it_can_delete_its_model_backend(self):
        doc1 = Article({'id': 1})

        # mock the model manager return
        mock_doc1 = Mock()
        mock_doc1.id = 1
        doc1._model_manager = Mock()
        doc1._model_manager.fetch.return_value = mock_doc1

        # delete the model
        doc1.delete()
        eq_([('delete', (doc1,))], doc1._model_manager.method_calls)

    def it_can_update_the_underlying_model(self):
        # Mock the actual django model
        DjangoModel = Mock(name='DjangoModel')

        class ModelDocument(documents.Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                # Use the mocked django model
                model = DjangoModel

        # create the mocked instance of the model, model_manager.fetch returns
        # it further down
        mock_model = Mock()
        mock_model.id = 24
        mock_model.name = "hello universe"

        # The expectation is that this instance gets newly created
        instance = ModelDocument({'id': 24, 'name': 'hello universe'})
        instance._model_manager = Mock()
        instance._model_manager.fetch.return_value = mock_model
        instance.update({'name': 'new name'})

        eq_('new name', instance.name)
        eq_([
            ('fetch', (instance,)),
            ('save', (instance,))], instance._model_manager.method_calls)


class when_a_document_contains_a_foreign_document_relation(unittest.TestCase):
    def it_can_render_the_document_inline(self):
        #prepare the setup
        mock_editor = Mock()
        mock_editor.id = 1
        mock_editor.age = 31
        mock_editor.first_name = 'Christo'
        mock_editor.last_name = 'Buschek'
        mock_editor.get_absolute_url.return_value = \
                "http://localhost/editor/1/"

        EditorModel.objects.get.return_value = mock_editor
        EditorModel.reset_mock()

        tag1 = Mock()
        tag1.slug = "tag1"
        tag1.get_absolute_url.return_value = "tag1_location"
        tag2 = Mock()
        tag2.slug = "tag2"
        tag2.get_absolute_url.return_value = "tag2_location"

        tagcloud = [tag2, tag1]
        tag_list = [tag2, tag1]

        def tag_side_effect(*args, **kwargs):
            return tag_list.pop()

        mock_article = Mock()
        mock_article.id = 1
        mock_article.name = "Headline"
        mock_article.get_absolute_url.return_value = "link"
        mock_article.editor = mock_editor

        mock_article.tags.all.return_value = tagcloud

        TagModel.objects.get.side_effect = tag_side_effect

        ArticleModel.objects.get.return_value = mock_article

        expected = {
                'id': 1,
                'name': 'Headline',
                'editor': {
                    'rel': 'related',
                    'href': 'http://localhost/editor/1/'
                    },
                'tags': [
                    {
                        "slug": "tag1",
                        "rel": "item",
                        "href": "tag1_location"
                        },
                    {
                        "slug": "tag2",
                        "rel": "item",
                        "href": "tag2_location"
                        },
                    ],
                'link': {
                    'rel': 'self',
                    'href': mock_article.get_absolute_url()
                    }
                }

        article = Article({'id': 1})
        article.fetch()
        eq_(expected, json.loads(article.to_json()))
        eq_([("objects.get", {
                "first_name": "Christo",
                "last_name": "Buschek"}
            )],
                EditorModel.method_calls)

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

    def it_can_map_the_relation_on_model_level_upon_creation(self):
        #This needs more thinking before proceeding
        #FIXME: This test should move into the model_tests
        raise SkipTest
        DjangoModel = Mock(name='DjangoModel')

        mock_model = Mock()
        mock_model.id = 34
        DjangoModel.objects.get.return_value = mock_model

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                model = DjangoModel

        OtherModel = Mock(name='OtherModel')
        OtherModel.DoesNotExist = Exception
        OtherModel.objects.get.side_effect = OtherModel.DoesNotExist

        class Other(Document):
            id = fields.NumberField()
            doc = fields.ForeignDocument(Doc)

            class Meta:
                model = OtherModel

        message = {
                "id": 1,
                "doc": 34
                }

        doc = Other(message)
        doc.save()

        eq_(True, DjangoModel.objects.get.called)
        DjangoModel.objects.get.assert_called_once_with(id=34)


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


class when_a_document_field_cant_be_mapped_to_a_model(unittest.TestCase):
    def it_can_provide_a_fetch_method(self):
        # Mock the actual django model
        DjangoModel = Mock(name='DjangoModel')

        class ModelDocument(documents.Document):
            id = fields.NumberField()
            name = fields.StringField()

            class Meta:
                # Use the mocked django model
                model = DjangoModel

            def fetch_name_field(self):
                return "Hello World"

            save_name_field = Mock()  # make sure this method has been called

        # create the mocked instance of the model
        mock_model = Mock()
        mock_model.id = 1

        # retrieve the document
        doc = ModelDocument({'id': 1})
        doc._model_manager = Mock()
        doc._model_manager.fetch.return_value = mock_model
        doc.fetch()

        eq_("Hello World", doc.name)

        # Now also save the document to the model, make sure the save overwrite
        # method is used. The save method of model_manager calls _save_state.
        doc._save_state()
        eq_(True, doc.save_name_field.called)
