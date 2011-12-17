import unittest

from nose.tools import eq_

from roa.fields import BooleanField, StringField


class when_a_boolean_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.bool_field = BooleanField(default=False)

    def it_has_a_default_value(self):
        eq_(False, self.bool_field.default)


class when_a_string_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.string_field = StringField(default='hello world')

    def it_has_a_default_value(self):
        eq_('hello world', self.string_field.default)
