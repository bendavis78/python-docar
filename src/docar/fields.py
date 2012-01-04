class NOT_PROVIDED:
    pass


class Field(object):
    # This counter is used to keep track of the order of declaration of fields.
    creation_counter = 0

    def __init__(self, default=NOT_PROVIDED, optional=False):
        self.default = default
        self.optional = optional

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


## Primitive Datatype
class BooleanField(Field):
    """A datatype representing true or false."""
    def __init__(self, *args, **kwargs):
        super(BooleanField, self).__init__(*args, **kwargs)


class StringField(Field):
    """A string datattype, a sequence of zero or more unicode characters."""
    def __init__(self, *args, **kwargs):
        super(StringField, self).__init__(*args, **kwargs)


class NumberField(Field):
    """A number datatype."""
    def __init__(self, *args, **kwargs):
        super(NumberField, self).__init__(*args, **kwargs)


## Structured Datatypes.

class CollectionField(Field):
    """An ordered list of zero or more referenced documents."""
    def __init__(self, *args, **kwargs):
        super(CollectionField, self).__init__(default=[], *args, **kwargs)


class ObjectField(Field):
    """An unordered list of zero or more key/value pairs referencing one
    document."""
    def __init__(self, *args, **kwargs):
        super(ObjectField, self).__init__(default={}, *args, **kwargs)


## Related Fields

class ForeignKey(Field):
    """A reference to another document."""
    def __init__(self, *args, **kwargs):
        super(ForeignKey, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        """Contribute ``self`` to ``cls``. Used to set several field specific
        attributes. Called during class creation in ``DocumentBase``."""
        super(ForeignKey, self).contribute_to_class(cls, name)

        cls._meta.add_related_field(self)
