import unittest

from nose.tools import eq_, assert_raises
from mock import Mock

from docar import fields
from docar.documents import Document
from docar.collections import Collection
from docar.exceptions import CollectionNotBound

# import the sample app
from app import Article, NewsPaper


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

    def it_fetches_all_documents_from_a_list(self):
        query_list = [
                {'id': 1},
                {'id': 2},
                {'id': 3},
                ]
        DjangoModel = Mock(name='DjangoModel')
        model_list = [Mock(), Mock(), Mock()]

        def get_side_effect(*args, **kwargs):
            return model_list.pop()

        DjangoModel.objects.get.side_effect = get_side_effect

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'django'
                model = DjangoModel

        class Col(Collection):
            document = Doc

        c = Col()

        # create a collection with all documents
        c.fetch_all(query_list)

        # The fetch_all must have created a collection with 3 documents
        eq_(3, len(c.collection_set))

        # The fetch_all must have queried 3x the backend model
        expected_calls = [
                ('objects.get', {'id': 1}),
                ('objects.get', {'id': 2}),
                ('objects.get', {'id': 3}),
                ]

        eq_(expected_calls, DjangoModel.method_calls)

    def it_can_append_new_documents(self):
        doc1 = Article({'id': 1, 'name': 'doc1'})
        newspaper = NewsPaper()

        eq_(0, len(newspaper.collection_set))
        newspaper.add(doc1)
        eq_(1, len(newspaper.collection_set))
        eq_([doc1], newspaper.collection_set)

    def it_can_delete_elements_from_its_set(self):
        doc1 = Article({'id': 1, 'name': 'doc1'})
        doc2 = Article({'id': 2, 'name': 'doc2'})
        doc3 = Article({'id': 3, 'name': 'doc3'})
        newspaper = NewsPaper()

        newspaper.collection_set= [doc1, doc2, doc3]

        eq_(3, len(newspaper.collection_set))

        # We remove the first element
        newspaper.delete({'id': 2})
        eq_(2, len(newspaper.collection_set))
        eq_(True, doc1 in newspaper.collection_set)
        eq_(True, doc3 in newspaper.collection_set)
        eq_(False, doc2 in newspaper.collection_set)

    def it_doesnt_add_instances_to_the_collection_that_are_not_documents(self):
        class A(object):
            pass

        newspaper = NewsPaper()

        eq_(0, len(newspaper.collection_set))
        newspaper.add(A())
        eq_(0, len(newspaper.collection_set))

    def it_can_turn_its_items_into_a_dict(self):
        class Doc(Document):
            id = fields.NumberField()

        class Col(Collection):
            document = Doc

        doc1 = Doc({'id': 1})
        doc2 = Doc({'id': 2})

        collection = Col([doc1, doc2])

        expected = [{'id': 1}, {'id': 2}]

        eq_(expected, collection._to_dict())

    def it_can_turn_itself_into_a_python_representation(self):
        class Doc(Document):
            id = fields.NumberField()

            def uri(self):
                return 'item_location'

        class Col(Collection):
            document = Doc

            def uri(self):
                return "collection_location"

        doc1 = Doc({'id': 1})
        doc2 = Doc({'id': 2})

        collection = Col([doc1, doc2])

        expected = {
            "size": 2,
            "items": [
                {'id': 1, 'link': {'rel': 'item', 'href': 'item_location'}},
                {'id': 2, 'link': {'rel': 'item', 'href': 'item_location'}}
                ],
            "link": {
                "rel": "self",
                "href": "collection_location"
                }
            }

        eq_(expected, collection.to_python())

    def it_can_render_the_whole_collection(self):
        class Doc(Document):
            id = fields.NumberField()
            name = fields.StringField(render=False)

            def uri(self):
                return 'item_location'

        class Col(Collection):
            document = Doc

            def uri(self):
                return "collection_location"

        doc1 = Doc({'id': 1, 'name': 'something'})
        doc2 = Doc({'id': 2, 'name': 'something'})

        collection = Col([doc1, doc2])

        expected = {
            "size": 2,
            "items": [
                {'id': 1, 'link': {'rel': 'item', 'href': 'item_location'}},
                {'id': 2, 'link': {'rel': 'item', 'href': 'item_location'}}
                ]
            }

        eq_(expected, collection.render())

    def it_can_fill_itself_from_a_queryset(self):
        class Doc(Document):
            id = fields.NumberField()

        class Col(Collection):
            document = Doc

        model1 = Mock()
        model2 = Mock()
        model1.id = 1
        model2.id = 2

        col = Col()

        eq_(0, len(col.collection_set))

        col._from_queryset([model1, model2])

        eq_(2, len(col.collection_set))

        doc1 = col.collection_set[0]
        doc2 = col.collection_set[1]

        eq_(True, isinstance(doc1, Doc))
        eq_(True, isinstance(doc2, Doc))
        eq_(1, doc1.id)
        eq_(2, doc2.id)
