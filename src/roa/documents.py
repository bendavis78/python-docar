import json
import types
import copy

from roa.fields import Field, NOT_PROVIDED


class DocumentBase(type):
    """Metaclass for the Document class."""

    def __new__(cls, name, bases, attrs):
        # populate the fields list
        fields = [
                (field_name, attrs.pop(field_name))
                for field_name, obj
                in attrs.items() if isinstance(obj, Field)
            ]

        # add the fields for each base class
        for base in bases[::-1]:
            if hasattr(base, 'base_fields'):
                fields = base.base_fields.items() + fields

        attrs['base_fields'] = dict(fields)
        new_class = super(DocumentBase, cls).__new__(cls, name, bases, attrs)

        # create the fields on the instance document
        for field_name, val in attrs['base_fields'].items():
            if val.default == NOT_PROVIDED:
                setattr(new_class, field_name, None)
            else:
                setattr(new_class, field_name, val.default)

        return new_class


class Document(object):
    """A document is a represantation."""
    __metaclass__ = DocumentBase

    def __init__(self, data=None):
        """Create a new document presentation of a resource.

        :param data: Initial values to use for this document.
        :type data: dict

        """
        self.fields = copy.deepcopy(self.base_fields)

        if not data:
            return

        if type(data) is not types.DictType:
            return

        # set the preloaded attributes
        for field_name, val in data.items():
            # We set simple fields, defer references and collections
            if type(val) == types.UnicodeType or \
                    type(val) == types.StringType or \
                    type(val) == types.BooleanType:
                setattr(self, field_name, val)

    def to_json(self):
        data = {}

        for field_name in self.fields.keys():
            data[field_name] = getattr(self, field_name)

        return json.dumps(data)

    def save(self):
        pass

    def validate(self):
        pass
