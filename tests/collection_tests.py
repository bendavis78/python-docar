import unittest

from nose.tools import eq_, assert_raises

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

    def it_can_append_new_documents(self):
        doc1 = Article({'id': 1, 'name': 'doc1'})
        newspaper = NewsPaper()

        eq_(0, len(newspaper.collection_set))
        newspaper.add(doc1)
        eq_(1, len(newspaper.collection_set))
        eq_([doc1], newspaper.collection_set)
