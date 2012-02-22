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


## Primitive Datatypes
class BooleanField(Field):
    """A datatype representing true or false."""
    field_type = "boolean"

    def __init__(self, *args, **kwargs):
        super(BooleanField, self).__init__(*args, **kwargs)


class StringField(Field):
    """A string datattype, a sequence of zero or more unicode characters."""
    field_type = "string"

    def __init__(self, *args, **kwargs):
        super(StringField, self).__init__(*args, **kwargs)


class NumberField(Field):
    """A number datatype."""
    field_type = "number"

    def __init__(self, *args, **kwargs):
        super(NumberField, self).__init__(*args, **kwargs)


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
