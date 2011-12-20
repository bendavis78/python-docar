class NOT_PROVIDED:
    pass


class Field(object):
    def __init__(self, default=NOT_PROVIDED):
        self.default = default


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
