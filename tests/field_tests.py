import unittest

from nose.tools import eq_

from roa import fields


class when_a_boolean_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.bool_field = fields.BooleanField(default=False)

    def it_has_a_default_value(self):
        eq_(False, self.bool_field.default)


class when_a_string_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.string_field = fields.StringField(default='hello world')

    def it_has_a_default_value(self):
        eq_('hello world', self.string_field.default)


class when_an_integer_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.integer_field = fields.IntegerField(default=1)

    def it_has_a_default_value(self):
        eq_(1, self.integer_field.default)
