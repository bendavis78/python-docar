import unittest
import types
import json

from nose.tools import eq_

from roa import documents
from roa import fields


BASKET = json.dumps({
        "is_rotten": True,
        "name": "Lovely Basket"
        })


class FruitBasket(documents.Document):
    is_rotten = fields.BooleanField(default=False)
    name = fields.StringField()


class SpecialFruitBasket(FruitBasket):
    is_present = fields.BooleanField()


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
        eq_(True, 'name' in self.basket.fields)

    def it_has_an_attribute_for_each_field(self):
        eq_(True, hasattr(self.basket, 'name'))
        eq_(types.NoneType, type(self.basket.name))

        eq_(True, hasattr(self.basket, 'is_rotten'))
        eq_(types.NoneType, type(self.basket.is_rotten))


class when_a_representation_is_parsed(unittest.TestCase):
    def setUp(self):
        self.basket = FruitBasket(BASKET)

    def it_has_the_fields_bound(self):
        eq_(True, self.basket.is_rotten)
        eq_('Lovely Basket', self.basket.name)


class when_a_document_inherits_from_another_document(unittest.TestCase):
    def setUp(self):
        self.basket = SpecialFruitBasket()

    def it_inherits_all_fields(self):
        # that should be the total amount of fields for the inherited document
        eq_(3, len(self.basket.fields))
        eq_(True, 'is_present' in self.basket.fields)
        eq_(True, 'is_rotten' in self.basket.fields)
        eq_(True, 'name' in self.basket.fields)
