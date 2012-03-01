from .exceptions import ValidationError


class NOT_PROVIDED:
    pass


class Field(object):
    # This counter is used to keep track of the order of declaration of fields.
    creation_counter = 0

    def __init__(self, default=NOT_PROVIDED, optional=False, context=[],
            render=True, scaffold=True):
        self.default = default
        self.optional = optional
        self.context = context
        self.render = render
        self.scaffold = scaffold

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

    def validate(self, value):
        if value is None and not self.optional:
            raise ValidationError("%s must be set." % self.name)
        #TODO: blank values
        #TODO: choices

    def clean(self, value):
        value = self.to_python(value)
        self.validate(value)

        return value

## Primitive Datatypes
class BooleanField(Field):
    """A datatype representing true or false."""
    field_type = "boolean"

    def __init__(self, *args, **kwargs):
        super(BooleanField, self).__init__(*args, **kwargs)

    def to_python(Self, value):
        if isinstance(value, bool) or isinstance(value, type(None)):
            return value
        elif value in ('t', 'True', 'true', 1):
            return True
        elif value in ('f', 'False', 'false', 0):
            return False
        raise ValidationError('%s must be either True or False' % str(value))


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
        if isinstance(value, int) or value is None:
            return value
        else:
            raise ValidationError('%s must be a integer.' % str(value))


## Derived Basic Types
class StaticField(StringField):
    """A static field that always has the same value."""
    field_type = "static"

    def __init__(self, *args, **kwargs):
        self.value = kwargs['value']
        del kwargs['value']
        super(StaticField, self).__init__(*args, **kwargs)


## Structured Datatypes.
class CollectionField(Field):
    """An ordered list of zero or more referenced documents."""
    field_type = "collection"

    def __init__(self, *args, **kwargs):
        self.Collection = args[0]
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