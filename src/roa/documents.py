import json
import types

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

        # create the fields on the instance document
        for field_name, val in attrs['fields'].items():
            setattr(new_class, field_name, val)

        return new_class


class Document(object):
    __metaclass__ = DocumentBase

    def __init__(self, data=None):
        if not data:
            return

        if type(data) is types.StringType:
            # Lets assume its a valid json string
            #FIXME: except json errors
            data = json.loads(data)

            # set the preloaded attributes
            for field_name, val in data.items():
                # We set simple fields, defer references and collections
                if type(val) == types.UnicodeType or \
                        type(val) == types.BooleanType:
                    setattr(self, field_name, val)

    def to_json(self):
        pass

    def save(self):
        pass

    def validate(self):
        pass
