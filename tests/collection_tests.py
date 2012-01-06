import unittest
import json

from nose.tools import eq_, assert_raises
from mock import Mock

from docar import fields
from docar.documents import Document
from docar.collections import Collection
from docar.exceptions import CollectionNotBound

# import the sample app
from app import Article, Editor, NewsPaper
from app import EditorModel


class when_a_collection_gets_instantiated(unittest.TestCase):
    def it_needs_to_be_bound_to_a_document(self):
        class Coll(Collection):
            pass

        assert_raises(CollectionNotBound, Coll)

    def it_accepts_a_list_of_documents(self):
        doc1 = Article({'id': 1, 'name': 'doc1'})
        doc2 = Article({'id': 2, 'name': 'doc2'})

        newspaper = NewsPaper([doc1, doc2])

        eq_(2, len(newspaper.collection_set))
        eq_([doc1, doc2], newspaper.collection_set)

    def it_can_append_new_documents(self):
        doc1 = Article({'id': 1, 'name': 'doc1'})
        newspaper = NewsPaper()

        eq_(0, len(newspaper.collection_set))
        newspaper.add(doc1)
        eq_(1, len(newspaper.collection_set))
        eq_([doc1], newspaper.collection_set)

    def it_doesnt_add_instances_to_the_collection_that_are_not_documents(self):
        class A(object):
            pass

        newspaper = NewsPaper()

        eq_(0, len(newspaper.collection_set))
        newspaper.add(A())
        eq_(0, len(newspaper.collection_set))

    def it_can_render_to_a_python_list(self):
        #prepare the setup
        mock_editor = Mock()
        mock_editor.id = 1
        mock_editor.age = 31
        mock_editor.first_name = 'Christo'
        mock_editor.last_name = 'Buschek'
        mock_editor.get_absolute_url.return_value = \
                "http://localhost/editor/1/"

        EditorModel.objects.get.return_value = mock_editor

        editor_dict = {'rel': 'related',
                'href': 'http://localhost/editor/1/'}

        MockModel = Mock()

        class MockDoc(Document):
            id = fields.NumberField()
            name = fields.StringField()
            editor = fields.ForeignDocument(Editor)

            class Meta:
                model = MockModel

        mock_article1 = Mock()
        mock_article1.id = 1
        mock_article1.name = "Headline"
        mock_article1.editor = mock_editor

        mock_article2 = Mock()
        mock_article2.id = 2
        mock_article2.name = "Headline"
        mock_article2.editor = mock_editor

        article_list = [mock_article2, mock_article1]

        def article_side_effect(*args, **kwargs):
            return article_list.pop()

        MockModel.objects.get.side_effect = article_side_effect

        doc1 = MockDoc({'id': 1})
        doc2 = MockDoc({'id': 2})

        newspaper = NewsPaper([doc1, doc2])

        expected = [
                {'id': 1, 'name': 'Headline', 'editor': editor_dict},
                {'id': 2, 'name': 'Headline', 'editor': editor_dict},
                ]

        eq_(expected, json.loads(newspaper.to_json()))
