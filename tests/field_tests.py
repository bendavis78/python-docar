import unittest

from nose.tools import eq_

from docar import fields, Document


class when_a_boolean_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.bool_field = fields.BooleanField(default=False)

    def it_has_a_default_value(self):
        eq_(False, self.bool_field.default)

    def it_is_not_optional(self):
        eq_(False, self.bool_field.optional)


class when_a_string_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.string_field = fields.StringField(default='hello world',
                optional=True)

    def it_has_a_default_value(self):
        eq_('hello world', self.string_field.default)

    def it_is_optional(self):
        eq_(True, self.string_field.optional)


class when_an_integer_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.integer_field = fields.NumberField(default=1)

    def it_has_a_default_value(self):
        eq_(1, self.integer_field.default)


class when_a_static_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.static_field = fields.StaticField(value="static")

    def it_has_a_value(self):
        eq_("static", self.static_field.value)


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
            f = fields.ForeignDocument(Article)

        #document = Mock(name="DocumentClass", spec=['id', '_meta'])

        eq_(True, hasattr(Klass, 'f'))


class when_a_collection_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.collection_field = fields.CollectionField("Collection")

    def it_defaults_to_NOT_PROVIDED(self):
        eq_(fields.NOT_PROVIDED, self.collection_field.default)

    def it_sets_the_collection_as_an_attribute(self):
        eq_("Collection", self.collection_field.Collection)
