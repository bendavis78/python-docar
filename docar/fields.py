from .exceptions import ValidationError


class NOT_PROVIDED:
    pass


class Field(object):
    # This counter is used to keep track of the order of declaration of fields.
    creation_counter = 0
    default_validators = []

    def __init__(self, default=NOT_PROVIDED, optional=False, context=[],
            render=True, scaffold=True, validators=[], validate=True,
            read_only=False):
        self.default = default
        self.optional = optional
        self.context = context
        self.render = render
        self.scaffold = scaffold
        self.validators = self.default_validators + validators
        self.validate = validate
        self.read_only = read_only

        # Set the creation counter. Increment it for each field declaration
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def __cmp__(self, other):
        # Needed for bisect, make sure the order of fields is preserved
        return cmp(self.creation_counter, other.creation_counter)

    def contribute_to_class(self, cls, name):
        """Contribute ``self`` to ``cls``. Used to set several field specific
        attributes. Called during class creation in ``DocumentBase``."""
        self.name = name
        self.document = cls
        cls._meta.add_field(self)

    def to_python(self, value):
        return value

    def run_validators(self, value):
        for validator in self.validators:
            validator(value)

    def validate_field(self, value):
        if hasattr(self, 'value'):
            # A static field, the value must be set anyway
            return
        if ((value is None or value is ""
            or isinstance(value, ForeignDocument)
            or isinstance(value, CollectionField))
                and (not self.optional and self.default is NOT_PROVIDED)):
            raise ValidationError("Field must be set.")
        #TODO: blank values
        #TODO: choices

    def clean(self, value):
        if not self.validate:
            return value

        value = self.to_python(value)
        self.validate_field(value)
        self.run_validators(value)

        return value

## Primitive Datatypes
class BooleanField(Field):
    """A datatype representing true or false."""
    field_type = "boolean"

    def __init__(self, *args, **kwargs):
        super(BooleanField, self).__init__(*args, **kwargs)

    def to_python(Self, value):
        if isinstance(value, bool):
            return value
        elif value in ('t', 'True', 'true', 1):
            return True
        elif value in ('f', 'False', 'false', 0):
            return False
        raise ValidationError('Must be either True or False')


class StringField(Field):
    """A string datattype, a sequence of zero or more unicode characters."""
    field_type = "string"

    def __init__(self, *args, **kwargs):
        super(StringField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        #TODO: Maybe return always unicode?
        if isinstance(value, str) or value is None:
            return value
        return str(value)


class NumberField(Field):
    """A number datatype."""
    field_type = "number"

    def __init__(self, *args, **kwargs):
        super(NumberField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, int):
            return value
        elif value is None:
            if self.default is not NOT_PROVIDED:
                return self.default
        raise ValidationError('Must be an integer.')


## Derived Basic Types
class StaticField(StringField):
    """A static field that always has the same value."""
    field_type = "static"

    def __init__(self, *args, **kwargs):
        self.value = kwargs['value']
        del kwargs['value']
        super(StaticField, self).__init__(*args, **kwargs)


class ChoicesField(StringField):
    """A field that provides a set of choices to choose from."""
    field_type = "choices"

    def __init__(self, *args, **kwargs):
        if not 'choices' in kwargs:
            self.choices = []
        else:
            self.choices = kwargs['choices']
            del(kwargs['choices'])

        super(ChoicesField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.choices:
            return value
        raise ValidationError('%s is not a valid choice.' % value)


## Structured Datatypes.
class CollectionField(Field):
    """An ordered list of zero or more referenced documents."""
    field_type = "collection"

    def __init__(self, *args, **kwargs):
        self.Collection = args[0]
        if 'inline' in kwargs:
            self.inline = kwargs['inline']
            del(kwargs['inline'])
        else:
            self.inline = False
        super(CollectionField, self).__init__(**kwargs)

    def contribute_to_class(self, cls, name):
        """Contribute ``self`` to ``cls``. Used to set several field specific
        attributes. Called during class creation in ``DocumentBase``."""
        super(CollectionField, self).contribute_to_class(cls, name)

        cls._meta.add_collection_field(self)


class ObjectField(Field):
    """An unordered list of zero or more key/value pairs referencing one
    document."""
    def __init__(self, *args, **kwargs):
        super(ObjectField, self).__init__(default={}, *args, **kwargs)


## Related Fields
class ForeignDocument(Field):
    """A reference to another document."""
    field_type = "foreign"

    def __init__(self, *args, **kwargs):
        self.Document = args[0]
        if 'inline' in kwargs:
            self.inline = kwargs['inline']
            del(kwargs['inline'])
        else:
            self.inline = False
        super(ForeignDocument, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        """Contribute ``self`` to ``cls``. Used to set several field specific
        attributes. Called during class creation in ``DocumentBase``."""
        super(ForeignDocument, self).contribute_to_class(cls, name)

        cls._meta.add_related_field(self)
