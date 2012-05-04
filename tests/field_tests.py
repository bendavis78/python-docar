import unittest

from nose.tools import eq_, assert_raises
from mock import Mock
from docar import fields, Document
from docar import exceptions


class when_a_field_gets_instantiated(unittest.TestCase):
    def it_can_have_a_validator_function(self):
        v1 = Mock()
        v2 = Mock()

        v2.side_effect = exceptions.ValidationError

        field = fields.StringField(validators=[v1, v2])
        field.name = "string_field"

        assert_raises(exceptions.ValidationError,
                field.run_validators, 'string_value')
        eq_(True, v1.called)
        eq_(True, v2.called)


class when_a_boolean_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.bool_field = fields.BooleanField(default=False)
        self.bool_field.name = "bool_field"

    def it_has_a_default_value(self):
        eq_(False, self.bool_field.default)

    def it_is_not_optional(self):
        eq_(False, self.bool_field.optional)

    def it_can_turn_itself_to_the_right_datatype(self):
        assert_raises(exceptions.ValidationError,
                self.bool_field.to_python, 'string')
        eq_(False, self.bool_field.to_python(0))
        eq_(True, self.bool_field.to_python(1))
        eq_(True, self.bool_field.to_python(True))
        eq_(False, self.bool_field.to_python(False))

    def it_can_clean_and_validate_itself(self):
        eq_(False, self.bool_field.clean(False))
        assert_raises(exceptions.ValidationError,
                self.bool_field.clean, 'string')
        assert_raises(exceptions.ValidationError,
                self.bool_field.clean, None)


class when_a_string_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.string_field = fields.StringField(default='hello world',
                optional=True)
        self.string_field.name = "string_field"

    def it_has_a_default_value(self):
        eq_('hello world', self.string_field.default)

    def it_is_optional(self):
        eq_(True, self.string_field.optional)

    def it_can_turn_itself_to_the_right_datatype(self):
        eq_(None, self.string_field.to_python(None))
        eq_('string', self.string_field.to_python('string'))
        eq_('0', self.string_field.to_python(0))
        eq_('False', self.string_field.to_python(False))

    def it_can_clean_and_validate_itself(self):
        eq_('string', self.string_field.clean('string'))
        # That one returns None cause the optional field is set
        eq_(None, self.string_field.clean(None))

class when_an_integer_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.integer_field = fields.NumberField(default=1)
        self.integer_field.name = "integer_field"

    def it_has_a_default_value(self):
        eq_(1, self.integer_field.default)

    def it_can_turn_itself_to_the_right_datatype(self):
        eq_(True, isinstance(self.integer_field.to_python(0), int))
        eq_(1, self.integer_field.to_python(None))
        assert_raises(exceptions.ValidationError, self.integer_field.to_python,
                'str')

    def it_can_clean_and_validate_itself(self):
        eq_(1, self.integer_field.clean(1))
        assert_raises(exceptions.ValidationError,
                self.integer_field.to_python, 'str')
        eq_(1, self.integer_field.clean(None))



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


class when_a_choices_field_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.choices_field = fields.ChoicesField(choices=['A', 'B'])

    def it_sets_the_coices_as_an_attribute(self):
        eq_(['A', 'B'], self.choices_field.choices)

    def it_returns_the_correct_value_if_its_a_valid_choic(self):
        eq_('A', self.choices_field.to_python('A'))

    def it_raises_a_validation_error_if_its_not_a_valid_choice(self):
        assert_raises(exceptions.ValidationError, self.choices_field.to_python,
                'C')
