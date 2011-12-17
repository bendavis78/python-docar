import unittest
import types

from nose.tools import eq_

from roa import documents
from roa import fields


class FruitBasket(documents.Document):
    is_rotten = fields.BooleanField(default=False)


class when_a_document_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.basket = FruitBasket()

    def it_has_a_to_json_method(self):
        #print dir(self)
        eq_(True, hasattr(self.basket, 'to_json'))

    def it_has_a_save_method(self):
        eq_(True, hasattr(self.basket, 'save'))

    def it_has_a_validate_method(self):
        eq_(True, hasattr(self.basket, 'validate'))

    def it_has_a_dict_of_fields(self):
        eq_(types.DictType, type(self.basket.fields))
        eq_(True, 'is_rotten' in self.basket.fields)
