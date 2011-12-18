class NOT_PROVIDED:
    pass


class Field(object):
    def __init__(self, default=NOT_PROVIDED):
        self.default = default


class BooleanField(Field):
    def __init__(self, *args, **kwargs):
        super(BooleanField, self).__init__(*args, **kwargs)


class StringField(Field):
    def __init__(self, *args, **kwargs):
        super(StringField, self).__init__(*args, **kwargs)


class IntegerField(Field):
    def __init__(self, *args, **kwargs):
        super(IntegerField, self).__init__(*args, **kwargs)
