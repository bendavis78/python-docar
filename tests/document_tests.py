import unittest
import types
import json

from nose.tools import eq_, assert_raises
from mock import Mock

from docar import documents
from docar import fields
from docar import Document
from docar.exceptions import ModelDoesNotExist
#from docar.exceptions import AmbigiousModelMapping

from app import Article, ArticleModel
from app import Editor, EditorModel


BASKET = {
        "is_rotten": True,
        "name": "Lovely Basket"
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

        EditorModel.objects.get.return_value = mock_editor

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

    def it_can_fetch_its_state_from_the_model_backend(self):
        doc1 = Article({'id': 1})

        # before we actually fetch the document, name should be empty
        eq_(None, doc1.name)

        # we mock the model object
        mock_model = ArticleModel.return_value

        ArticleModel.objects.get.return_value = mock_model
        mock_model.id = 1
        mock_model.name = "hello"

        # this should all work out now
        doc1.fetch()
        eq_("hello", doc1.name)

        # mock the manager object, It should throw an exception
        ArticleModel.objects.get.side_effect = ArticleModel.DoesNotExist

        assert_raises(ModelDoesNotExist, doc1.fetch)

    def it_can_delete_its_model_backend(self):
        doc1 = Article({'id': 1})

        # we mock the model object
        mock_model = ArticleModel.return_value
        ArticleModel.objects.get.return_value = mock_model

        # delete the model
        doc1.delete()
        eq_([('delete',)], mock_model.method_calls)

    def it_can_link_to_other_documents(self):
        #editor = Editor({'first_name': 'Christo', 'last_name': 'Buschek'})
        #doc1 = Article({'id': 1, 'editor': editor})
        pass


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
        eq_(3, len(self.basket.fields))
        eq_(True, 'is_present' in self.basket.fields)
        eq_(True, 'is_rotten' in self.basket.fields)
        eq_(True, 'name' in self.basket.fields)


class when_a_document_is_bound(unittest.TestCase):
    def setUp(self):
        self.basket = FruitBasket()
        self.basket.name = 'Lovely Basket'
        self.basket.is_rotten = True

    def it_can_render_to_json(self):
        eq_(json.dumps(BASKET), self.basket.to_json())

    def it_can_be_rendered_to_a_python_dictionary(self):
        eq_(BASKET, self.basket.to_attributes())

    def it_can_collect_links(self):
        eq_('http://localhost/basket/1/', self.basket.uri())

    def it_can_provide_a_link_using_the_django_model(self):
        mock_editor = Mock()
        mock_editor.get_absolute_url.return_value = \
                "http://localhost/editor/1/"
        EditorModel.objects.get.return_value = mock_editor

        editor = Editor({'id': 1})
        editor.fetch()
        eq_("http://localhost/editor/1/", editor.uri())

    def it_can_be_saved_to_a_django_model(self):
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
        DjangoModel.DoesNotExist = Exception
        DjangoModel.objects.get.side_effect = DjangoModel.DoesNotExist

        # The expectation is that this instance gets newly created
        instance = ModelDocument({'id': 23, 'name': 'hello world'})
        instance.save()

        eq_(True, DjangoModel.objects.get.called)
        eq_(True, DjangoModel.called)
        eq_(True, mock_model.save.called)
        # The attributes of the model should be set
        eq_(23, mock_model.id)
        eq_('hello world', mock_model.name)

        # Now don't create a new model, but update an existing one
        # mock the manager object, It should throw an exception
        DjangoModel.DoesNotExist = Exception
        DjangoModel.objects.get.return_value = mock_model

        # The expectation is that this instance gets newly created
        instance = ModelDocument({'id': 24, 'name': 'hello universe'})
        instance.save()

        eq_(True, DjangoModel.objects.get.called)
        eq_(True, DjangoModel.called)
        eq_(True, mock_model.save.called)
        # The attributes of the model should be set
        eq_(24, mock_model.id)
        eq_('hello universe', mock_model.name)


class when_a_document_contains_a_foreign_document_relation(unittest.TestCase):
    def it_can_render_the_document_inline(self):
        #prepare the setup
        mock_editor = Mock()
        mock_editor.age = 31
        mock_editor.first_name = 'Christo'
        mock_editor.last_name = 'Buschek'
        mock_editor.get_absolute_url.return_value = \
                "http://localhost/editor/1/"

        EditorModel.objects.get.return_value = mock_editor

        mock_article = Mock()
        mock_article.id = 1
        mock_article.name = "Headline"
        mock_article.editor = mock_editor

        ArticleModel.objects.get.return_value = mock_article

        expected = {
                'id': 1,
                'name': 'Headline',
                'editor': {
                    'rel': 'related',
                    'href': 'http://localhost/editor/1/'
                    }
                }

        article = Article({'id': 1})
        article.fetch()

        eq_(expected, json.loads(article.to_json()))
