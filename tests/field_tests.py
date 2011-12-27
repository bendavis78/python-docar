import unittest

from nose.tools import eq_

from roa import fields, Document


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
        self.integer_field = fields.NumberField(default=1)

    def it_has_a_default_value(self):
        eq_(1, self.integer_field.default)


class when_an_object_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.object_field = fields.ObjectField()

    def it_is_an_empty_dict(self):
        eq_({}, self.object_field.default)


class when_a_foreign_key_field_gets_instantiated(unittest.TestCase):
    def it_sets_to_different_attributes_to_the_class(self):
        class Article(Document):
            # a simple target document
            id = fields.NumberField()

        class Klass(Document):
            id = fields.NumberField()
            f = fields.ForeignKey(Article)

        #document = Mock(name="DocumentClass", spec=['id', '_meta'])

        eq_(True, hasattr(Klass, 'f'))
        eq_(True, hasattr(Klass, 'f_id'))


class when_a_collection_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.collection_field = fields.CollectionField()

    def it_is_an_empty_list(self):
        eq_([], self.collection_field.default)
