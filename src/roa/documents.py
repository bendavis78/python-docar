import json
import types
import copy

from bisect import bisect

from roa.fields import Field, NOT_PROVIDED


DEFAULT_NAMES = ('identifier', 'model', 'excludes')


def clean_meta(Meta):
    """Clean the Meta class from internal attributes."""
    if not Meta:
        return
    CleanedMeta = Meta.__dict__.copy()
    for name in Meta.__dict__:
        if name.startswith('_'):
            del CleanedMeta[name]

    return CleanedMeta


class Options(object):
    """A option class used to initiate documents in a sane state."""
    def __init__(self, meta):
        # Initialize some default values
        self.model = None
        self.identifier = 'id'
        # FIXME: Do some type checking
        self.excludes = []
        self.local_fields = []

        self.meta = meta

    def update(self, options={}):
        for option, value in options.items():
            setattr(self, option, value)

    def add_field(self, field):
        """Insert field into this documents fields."""
        self.local_fields.insert(bisect(self.local_fields, field), field)

    def contribute_to_class(self, cls, name):
        # This is bluntly stolen from django
        # Set first thedefault values
        cls._meta = self

        # Then override it with values from the ``Meta`` class
        if self.meta:
            meta_attrs = self.meta
            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))


class DocumentBase(type):
    """Metaclass for the Document class."""

    def __new__(cls, name, bases, attrs):
        new_class = super(DocumentBase, cls).__new__(cls, name, bases, attrs)
        parents = [b for b in bases if isinstance(b, DocumentBase)]

        attr_meta = attrs.pop('Meta', None)
        meta_attrs = clean_meta(attr_meta)

        # set the defaults
        new_class.add_to_class('_meta', Options(meta_attrs))

        # set all attributes to the class
        for name, obj in attrs.items():
            new_class.add_to_class(name, obj)

        for base in parents:
            if not hasattr(base, '_meta'):
                continue
            for field in base._meta.local_fields:
                new_class.add_to_class(field.name, field)

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

    def add_to_class(cls, name, obj):
        """If the obj provides its own contribute method, call it, otherwise
        attach this object to the class."""
        if hasattr(obj, 'contribute_to_class'):
            obj.contribute_to_class(cls, name)
        else:
            setattr(cls, name, obj)


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
            # FIXME: Shouldn't the validator do that???
            if type(val) == types.UnicodeType or \
                    type(val) == types.StringType or \
                    type(val) == types.BooleanType or \
                    type(val) == types.IntType:
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

        # populate the obj with the documents state
        for field in self._meta.local_fields:
            setattr(obj, field.name, getattr(self, field.name))
        obj.save()

    def validate(self):
        pass

    def uri(self):
        """Return the absolute uri for this resource.

        :return: The URI of this resource.
        :rtype: string

        Implement this method on your document if you have special needs for
        the form of the URI.

        .. note::

            This method should always return the absolute URI as a string.

        """
        return self._compute_uri()

    def _compute_uri(self):
        """The mechanism to compute the uri of this resource."""
        #FIXME: Implement the django get_absolute_uri handler
        pass
