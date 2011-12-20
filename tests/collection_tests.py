import unittest

from nose.tools import eq_

# import the sample app
from app import Article, NewsPaper


class when_a_collection_gets_instantiated(unittest.TestCase):
    def it_accepts_a_list_of_documents(self):
        doc1 = Article({'id': 1, 'name': 'doc1'})
        doc2 = Article({'id': 2, 'name': 'doc2'})

        newspaper = NewsPaper([doc1, doc2])

        eq_(2, len(newspaper.collection_set))
        eq_([doc1, doc2], newspaper.collection_set)
