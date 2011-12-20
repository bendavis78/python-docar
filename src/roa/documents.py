import json
import types
import copy

from roa.fields import Field, NOT_PROVIDED


class Options(object):
    """A option class used to initiate documents in a sane state."""
    def __init__(self, model=None, excludes=[], identifier='id'):
        self.model = model
        self.identifier = identifier
        # FIXME: Do some type checking
        self.excludes = excludes


class DocumentBase(type):
    """Metaclass for the Document class."""

    def __new__(cls, name, bases, attrs):
        new_class = super(DocumentBase, cls).__new__(cls, name, bases, attrs)

        # set the defaults
        setattr(new_class, '_meta', Options())

        attr_meta = attrs.pop('Meta', None)

        #print attr_meta
        if attr_meta:
            meta_attrs = attr_meta.__dict__.copy()
            for name, value in attr_meta.__dict__.items():
                if name.startswith('_'):
                    del meta_attrs[name]
                    continue
                setattr(new_class._meta, name, meta_attrs.pop(name))

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

        #attrs['base_fields'] = dict(fields)
        setattr(new_class, 'base_fields', dict(fields))

        # create the fields on the instance document
        for field_name, val in new_class.base_fields.items():
            if val.default == NOT_PROVIDED:
                setattr(new_class, field_name, None)
            else:
                setattr(new_class, field_name, val.default)

        return new_class


class Document(object):
    """A document is a representation."""
    __metaclass__ = DocumentBase

    def __init__(self, data=None):
        """Create a new document presentation of a resource.

        :param data: Initial values to use for this document.
        :type data: dict

        """
        self.fields = copy.deepcopy(self.base_fields)

        # Check on the input
        if (not data or
                type(data) is not types.DictType):
            return

        # set the preloaded attributes
        for field_name, val in data.items():
            # We set simple fields, defer references and collections
            if type(val) == types.UnicodeType or \
                    type(val) == types.StringType or \
                    type(val) == types.BooleanType:
                setattr(self, field_name, val)

    def to_json(self):
        """Render this document as json."""
        return json.dumps(self.to_attributes())

    def to_attributes(self):
        """Render this document to a python dictionary."""
        data = {}

        for field_name in self.fields.keys():
            data[field_name] = getattr(self, field_name)

        return data

    def save(self):
        """Save the document in a django model backend."""
        #FIXME: Handle the fact if the document is not mapped to a model
        # First see if the model already exists
        try:
            obj = self._meta.model.objects.get(id=self.id)
        except self._meta.model.DoesNotExist:
            # We assume it gets newly created
            obj = self._meta.model()

        obj.save()

    def validate(self):
        pass

    def uri(self):
        """Return the absolute uri for this resource."""
        return self._compute_uri()

    def _compute_uri(self):
        """The mechanism to compute the uri of this resource."""
        #FIXME: Implement the django get_absolute_uri handler
        pass
