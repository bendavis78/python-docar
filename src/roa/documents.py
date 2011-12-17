from roa.fields import Field


class DocumentBase(type):
    def __new__(cls, name, bases, attrs):
        # populate the fields dict
        fields = [
                (field_name, attrs.pop(field_name))
                for field_name, obj
                in attrs.items() if isinstance(obj, Field)
            ]
        attrs['fields'] = dict(fields)
        new_class = super(DocumentBase, cls).__new__(cls, name, bases, attrs)

        return new_class


class Document(object):
    __metaclass__ = DocumentBase

    def to_json(self):
        pass

    def save(self):
        pass

    def validate(self):
        pass
