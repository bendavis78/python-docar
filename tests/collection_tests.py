import unittest

from nose.tools import eq_

from roa import Collection
from roa import Document
from roa import fields


class Article(Document):
    id = fields.NumberField()
    name = fields.StringField()

    class Meta:
        model = 'Article'


class NewsPaper(Collection):
    document = Article


class when_a_collection_gets_instantiated(unittest.TestCase):
    def it_accepts_a_list_of_documents(self):
        doc1 = Article({'id': 1, 'name': 'doc1'})
        doc2 = Article({'id': 2, 'name': 'doc2'})

        newspaper = NewsPaper([doc1, doc2])

        eq_(2, len(newspaper.collection_set))
        eq_([doc1, doc2], newspaper.collection_set)
