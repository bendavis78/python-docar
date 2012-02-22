import json
import types

from bisect import bisect

from .fields import ForeignDocument, CollectionField, NOT_PROVIDED
from .backends import BackendManager


DEFAULT_NAMES = ('identifier', 'model', 'excludes', 'backend_type', 'context',
        'render')


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
        self.backend_type = 'django'
        self.identifier = ['id']
        # FIXME: Do some type checking
        self.excludes = []
        self.context = []
        self.local_fields = []
        self.related_fields = []
        self.collection_fields = []
        self.render = True

        self.meta = meta

    def add_field(self, field):
        """Insert field into this documents fields."""
        self.local_fields.insert(bisect(self.local_fields, field), field)

    def add_related_field(self, field):
        """Insert a related field into the documents fields."""
        self.related_fields.insert(bisect(self.related_fields, field), field)

    def add_collection_field(self, field):
        """Insert a collection field into the documents fields."""
        self.collection_fields.insert(bisect(self.collection_fields, field),
                field)

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

        # create the fields on the instance document
        for field in new_class._meta.local_fields:
            if isinstance(field, CollectionField):
                collection = field.Collection()
                collection.bound = False
                setattr(new_class, field.name, collection)
            elif isinstance(field, ForeignDocument):
                document = field.Document()
                document.bound = False
                setattr(new_class, field.name, document)
            elif field.default == NOT_PROVIDED:
                setattr(new_class, field.name, None)
            else:
                setattr(new_class, field.name, field.default)

        # create the related fields on the instance document
        #FIXME: not sure if thats really needed
        #for field in new_class._meta.related_fields:
        #    setattr(new_class, "%s_id" % field.name, None)

        # Add the model manager if a model is set
        new_class._backend_manager = BackendManager(
                new_class._meta.backend_type)
        if new_class._meta.backend_type in 'django':
            new_class._backend_manager._model = new_class._meta.model

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

    _context = {}
    bound = False

    def __init__(self, data=None, context={}):
        """Create a new document presentation of a resource.

        :param data: Initial values to use for this document.
        :type data: dict
        :param context: Add additional context that can be used by the backend.
        :type context: dict

        """
        # Check on the input
        if (not data or
                type(data) is not types.DictType):
            return

        self._context = context

        # set the preloaded attributes
        for field_name, val in data.items():
            # We set simple fields, defer references and collections
            # FIXME: Shouldn't the validator do that???
            if type(val) == types.UnicodeType or \
                    type(val) == types.StringType or \
                    type(val) == types.BooleanType or \
                    type(val) == types.IntType:
                setattr(self, field_name, val)
            elif type(val) == types.ListType:
                # Create a collection containing the list items
                collection = getattr(self, field_name)
                # for each member of the list, create a document, and add it to
                # the collection
                for item in val:
                    doc = collection.document(item)
                    collection.add(doc)
                if len(collection.collection_set) > 0:
                    # If we have at least one member in the collection, we
                    # regard it as bound
                    collection.bound = True
                # set the collection as document attribute
                setattr(self, field_name, collection)
            elif type(val) == types.DictType:
                # We got ourselve a foreign document
                Document = [field.Document
                        for field in self._meta.related_fields
                        if field.name in field_name]
                if not Document:
                    # If we didn't find it in the related_fields list, its not
                    # a foreign document, so we ignore this dict field
                    continue
                # create the appropriate document and set it as an attribute
                doc = Document[0](data=val, context=context)
                # We have a bound foreign document
                doc.bound = True
                setattr(self, field_name, doc)

    def _identifier_state(self):
        data = {}
        for elem in self._meta.identifier:
            if hasattr(self, "fetch_%s_field" % elem):
                fetch_field = getattr(self, "fetch_%s_field" % elem)
                data[elem] = fetch_field()
            elif hasattr(self, "save_%s_field" % elem):
                save_field = getattr(self, "save_%s_field" % elem)
                data[elem] = save_field()
            else:
                data[elem] = getattr(self, elem)
        return data

    def _get_context(self):
        if len(self._context) < 1:
            # If we have no context meta option set, just return it as it is
            return self._context

        obj = {}
        for field in self._meta.context:
            obj[field] = self._context[field]

        return obj

    def _prepare_fetch(self):
        """Create a dict with the document state, and apply all
        ``fetch_FIELD_field`` methods."""
        #FIXME: Handle the fact if the document is not mapped to a model
        data = {}

        # populate the data_dict with the documents state
        for field in self._meta.local_fields:
            if hasattr(self, "map_%s_field" % field.name):
                # We have a fetch method for this field
                map_field = getattr(self, "map_%s_field" % field.name)
                data[field.name] = map_field()

                # skip to the next iteration
                continue

            # No save method has been provided, lets map the fields one to one.
            data[field.name] = getattr(self, field.name)

        return data

    def _prepare_save(self):
        """Create a dict with the document state, and apply all
        ``save_FIELD_field`` methods."""
        #FIXME: Handle the fact if the document is not mapped to a model
        data = {}

        # populate the data_dict with the documents state
        for field in self._meta.local_fields:
            if hasattr(self, "save_%s_field" % field.name):
                # We have a save method for this field
                save_field = getattr(self, "save_%s_field" % field.name)
                data[field.name] = save_field()
            elif isinstance(getattr(self, field.name), type(None)):
                # We also ignore any field that is set to None
                continue
            elif (field.optional is True
                    and (isinstance(field, ForeignDocument)
                        or isinstance(field, CollectionField))
                    and (getattr(getattr(self, field.name),
                        'bound') is False)):
                # The field is optional and not bound, so we ignore it for the
                # backend state. This should only be done for foreign documents
                # and collections
                continue
            else:
                # no save method found, map the field 1-1
                data[field.name] = getattr(self, field.name)

        return data

    def to_json(self):
        """Render this document as json."""
        return json.dumps(self.to_python())

    def to_python(self):
        """Render this document to a python dictionary."""
        data = self._prepare_render()

        # add the link to itself
        data['link'] = {
                'rel': 'self',
                'href': self.uri()}
        return data

    def _prepare_render(self):
        """Create a proper python dict that can be further rendered."""
        data = {}
        related = {}

        # Cycle all registered fields, and fill the data dict
        for field in self._meta.local_fields:
            if field.optional and not getattr(self, field.name):
                # The field is optional and not set, ignore it
                continue
            elif not field.render:
                continue
            elif hasattr(self, "render_%s_field" % field.name):
                # We have a render method for this field
                render_field = getattr(self, "render_%s_field" % field.name)
                data[field.name] = render_field()
                # skip to the next iteration
                continue
            elif isinstance(field, ForeignDocument):
                # fill the related dict
                elem = getattr(self, field.name)
                if not elem.bound and field.optional:
                    # we don't render foreign documents that are optional and
                    # not set.
                    continue
                if field.inline:
                    # we render the field inline
                    related[field.name] = elem._prepare_render()
                else:
                    related[field.name] = {
                            'rel': 'related',
                            'href': elem.uri()}
                    # Also add the identifier fields into the rendered output
                    identifiers = {}
                    for id_field in elem._meta.identifier:
                        identifiers[id_field] = getattr(elem, id_field)
                    related[field.name].update(identifiers)

            elif isinstance(field, CollectionField):
                attr = getattr(self, field.name)
                data[field.name] = attr._prepare_render()
            else:
                data[field.name] = getattr(self, field.name)
        # update the data dict with the related fields
        data.update(related)

        return data

    def _init_from_dict(self, obj):
        """Set the document state from this dictionary."""
        for k, v in obj.iteritems():
            if isinstance(v, dict):
                # assume a foreign document
                doc = getattr(self, k)
                Document = [field.Document
                        for field in self._meta.related_fields
                        if field.name in k]
                if not Document:
                    # If we didn't find it in the related_fields list, its not
                    # a foreign document, so we ignore this dict field
                    continue
                doc = Document[0](v, context=self._context)
                doc.bound = True
                doc._init_from_dict(v)
                setattr(self, k, doc)
            elif isinstance(v, list):
                col = getattr(self, k)
                col.collection_set = []
                col.bound = False
                for item in v:
                    doc = col.document(item, context=self._context)
                    doc.bound = True
                    doc._init_from_dict(item)
                    col.add(doc)
                setattr(self, k, col)
            else:
                setattr(self, k, v)

    def save(self, *args, **kwargs):
        """Save the document in a django model backend."""
        self._backend_manager.save(self, *args, **kwargs)

    def update(self, data, *args, **kwargs):
        self.fetch(*args, **kwargs)

        # First update the own document state with the new values
        self._init_from_dict(data)

        # save the representation to the model
        self.save(*args, **kwargs)

    def fetch(self, **kwargs):
        """Fetch the model from the backend to create the representation of
        this resource."""
        # Retrieve the object from the backend
        obj = self._backend_manager.fetch(self, **kwargs)

        # Update the document
        for k, v in obj.iteritems():
            setattr(self, k, v)

    def delete(self, **kwargs):
        """Delete a model instance associated with this document."""
        #self._backend_manager.delete(self._meta.identifier,
        #        **self._prepare_save())
        self._backend_manager.delete(self, **kwargs)

    def uri(self):
        """Return the absolute uri for this resource.

        :return: The URI of this resource.
        :rtype: string

        Implement this method on your document if you have special needs for
        the form of the URI.

        .. note::

            This method should always return the absolute URI as a string.

        """
        return self._backend_manager.uri()

    def scaffold(self):
        """Return a scaffold of this document.

        :return: A scaffolded document.
        :rtype: dict

        """
        data = {}
        for field in self._meta.local_fields:
            if not field.scaffold:
                # scaffolding is disabled for this field
                continue
            value = getattr(self, field.name)
            if field.field_type in "static":
                # We dont scaffold static fields per default
                continue
            elif field.field_type in "foreign":
                # If we found a foreign document, we recurse into the scaffold
                # method of that document
                data[field.name] = value.scaffold()
            elif field.field_type in "collection":
                # We scaffold each document item of the collection set
                data[field.name] = []
                for item in value.collection_set:
                    data[field.name].append(item.scaffold())
            elif isinstance(value, type(None)):
                # If we have a not set value and its optional, skip it for the
                # scaffolding
                if field.optional:
                    continue

                # There is no value set yet for this field, so we set it
                # depependent on the field type
                if field.field_type in "string":
                    data[field.name] = ""
                else:
                    data[field.name] = None
            else:
                data[field.name] = value

        return data
