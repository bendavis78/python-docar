import json
import types
import copy

from bisect import bisect

from .fields import Field, ForeignDocument, CollectionField, NOT_PROVIDED
from .models import ModelManager
#AmbigiousModelMapping


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
        self.identifier = ['id']
        # FIXME: Do some type checking
        self.excludes = []
        self.local_fields = []
        self.related_fields = []

        self.meta = meta

    def add_field(self, field):
        """Insert field into this documents fields."""
        self.local_fields.insert(bisect(self.local_fields, field), field)

    def add_related_field(self, field):
        """Insert a related field into the documents fields."""
        self.related_fields.insert(bisect(self.local_fields, field), field)

    def contribute_to_class(self, cls, name):
        # This is bluntly stolen from the django orm
        # Set first the default values
        cls._meta = self

        # Then override it with values from the ``Meta`` class
        if self.meta:
            meta_attrs = self.meta

            # We should make sure that `identifier` is a list
            if 'identifier' in meta_attrs:
                if type(meta_attrs['identifier']) is types.StringType:
                    # we assume the identifier has been specified as a string
                    meta_attrs['identifier'] = [meta_attrs['identifier']]

            for attr_name in DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                #elif hasattr(self.meta, attr_name):
                #    setattr(self, attr_name, getattr(self.meta, attr_name))


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
            for field in base._meta.local_fields:
                new_class.add_to_class(field.name, field)

        #FIXME: Not sure if I need fields and base_fields
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

        # create the related fields on the instance document
        for field in new_class._meta.related_fields:
            setattr(new_class, "%s_id" % field.name, None)

        # Add the model manager
        new_class._model_manager = ModelManager('django')
        new_class._model_manager._model = new_class._meta.model

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
        #FIXME: Do I actualy need this attribute?
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
        related = {}

        # Cycle all registered fields, and fill the data dict
        for field in self._meta.local_fields:
            if field.optional and not getattr(self, field.name):
                # The field is optional and not set, ignore it
                continue
            if isinstance(field, ForeignDocument):
                #FIXME: determine not bound or optional foreign documents
                # fill the related dict
                elem = getattr(self, field.name)
                related[field.name] = {
                        'rel': 'related',
                        'href': elem.uri()}
            elif isinstance(field, CollectionField):
                collection = self._model_manager._get_collection(field)
                data[field.name] = collection.to_attributes()
            else:
                data[field.name] = getattr(self, field.name)
        # update the data dict with the related fields
        data.update(related)

        # add the link to itself
        data['link'] = {
                'rel': 'self',
                'href': self.uri()}
        return data

    def _get_document_state(self):
        #FIXME: Handle the fact if the document is not mapped to a model
        data = {}

        # populate the data_dict with the documents state
        for field in self._meta.local_fields:
            if hasattr(self, "save_%s_field" % field.name):
                # We have a save method for this field
                save_field = getattr(self, "save_%s_field" % field.name)
                data[field.name] = save_field()

                # skip to the next iteration
                continue

            # No save method has been provided, lets map the fields one to one.
            data[field.name] = getattr(self, field.name)

        return data

    def save(self):
        """Save the document in a django model backend."""
        self._model_manager.save(self._meta.identifier,
                **self._get_document_state())

    def update(self, data):
        # FIXME: Handle ForeignDocument relations
        # First update the own document state with the new values
        for k, v in data.iteritems():
            setattr(self, k, v)

        # save the representation to the model
        self.save()

    def fetch(self):
        """Fetch the model from the backend to create the representation of
        this resource."""
        params = {}
        # Construct the query dict
        for elem in range(len(self._meta.identifier)):
            params[self._meta.identifier[elem]] = getattr(self,
                    self._meta.identifier[elem])

        # Retrieve the object from the backend
        obj = self._model_manager.fetch(**params)

        self._meta.model_instance = obj

        for field in self._meta.local_fields:
            if hasattr(self, "fetch_%s_field" % field.name):
                # If the document provides a fetch method for this field, use
                # that one
                fetch_field = getattr(self, "fetch_%s_field" % field.name)
                setattr(self, field.name, fetch_field())
            elif isinstance(field, ForeignDocument):
                # retrieve the related document
                kwargs = {}
                related_instance = getattr(obj, field.name)
                Document = field.Document
                for identifier in Document._meta.identifier:
                    kwargs[identifier] = getattr(related_instance, identifier)
                document = Document(kwargs)
                document.fetch()
                setattr(self, field.name, document)
            elif hasattr(obj, field.name):
                # Otherwise set the value of the field from the retrieved model
                # object
                setattr(self, field.name, getattr(obj, field.name))

    def delete(self):
        """Delete a model instance associated with this document."""
        self._model_manager.delete(self._meta.identifier,
                **self._get_document_state())

    def uri(self):
        """Return the absolute uri for this resource.

        :return: The URI of this resource.
        :rtype: string

        Implement this method on your document if you have special needs for
        the form of the URI.

        .. note::

            This method should always return the absolute URI as a string.

        """
        return self._model_manager.uri()
