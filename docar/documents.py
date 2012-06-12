import json
import types

from bisect import bisect

from .fields import (ForeignDocument,
        CollectionField,
        StaticField,
        NOT_PROVIDED)

from .backends import BackendManager
from .exceptions import ValidationError, BackendDoesNotExist


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
        self.backend_type = None
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
            elif isinstance(field, StaticField):
                setattr(new_class, field.name, field.value)
            else:
                setattr(new_class, field.name, field.default)

        # Add the model manager if a model is set
        if not new_class._meta.backend_type:
            new_class._backend_manager = None
        else:
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

        :param data: Initial values to use for this document. Specify at least
                     the identifier to be able to fetch the resource.
        :type data: dict
        :param context: Add additional context that can be used by the backend.
                        Use this to provide extra values to be used by a
                        backend that are not set in the representation.
        :type context: dict

        """
        # Check on the input
        if (not data or
                type(data) is not types.DictType):
            return

        self._context = context
        self._from_dict(data)
        self.bound = True

    def _to_dict(self):
        """Return the document as a python dictionary. This method recursively
        turns related documents and items of collections into dictionaries
        too."""
        data = {}

        for field in self._meta.local_fields:
            if field.optional and not getattr(self, field.name):
                # The field is optional and none, ignore it
                continue
            if (field.optional is True
                    and (isinstance(field, ForeignDocument)
                        or isinstance(field, CollectionField))
                    and (getattr(getattr(self, field.name),
                        'bound') is False)):
                # The field is optional and not bound, so we ignore it for the
                # backend state. This should only be done for foreign documents
                # and collections
                continue
            if isinstance(field, ForeignDocument):
                related = getattr(self, field.name)
                data[field.name] = related._to_dict()
            elif isinstance(field, CollectionField):
                col = getattr(self, field.name)
                data[field.name] = []
                for item in col.collection_set:
                    data[field.name].append(item._to_dict())
            elif isinstance(field, StaticField):
                data[field.name] = field.value
            else:
                data[field.name] = getattr(self, field.name)

        return data

    def _from_dict(self, obj):
        """Create the document from a dict structure. It recursively builds
        also related documents and collections from a dictionary input."""
        for item, value in obj.iteritems():
            if isinstance(value, dict):
                fields = [f for f in self._meta.related_fields
                        if f.name == item]
                if len(fields) > 0:
                    field = fields[0]
                else:
                    continue
                Document = field.Document
                # Lets create a new relation
                document = Document(value, context=self._context)
                setattr(self, item, document)
            elif isinstance(value, list):
                # a collection
                field = [f for f in self._meta.local_fields
                        if f.name == item][0]
                collection = field.Collection()
                collection.collection_set = []
                Document = collection.document
                for elem in value:
                    document = Document(elem, context=self._context)
                    collection.add(document)
                if len(collection.collection_set) > 0:
                    # If we have at least one member in the collection, we
                    # regard it as bound
                    collection.bound = True
                setattr(self, item, collection)
            else:
                setattr(self, item, value)

    def _from_model(self, model):
        """Fill the document from a django model."""
        #FIXME: Add some type checking whether `model` truly is a django model
        for field in self._meta.local_fields:
            name = field.name
            mapped_name = name

            # We map document field names to names of fields on the backend
            # models.
            if hasattr(self, "map_%s_field" % name):
                map_method = getattr(self, "map_%s_field" % name)
                mapped_name = map_method()

            # skip fields that are not set on the model
            if not hasattr(model, mapped_name):
                continue

            if isinstance(field, ForeignDocument):
                related_model = getattr(model, mapped_name)
                foreign_document = field.Document({},
                        context=self._get_context())
                foreign_document._from_model(related_model)
                setattr(self, name, foreign_document)

            elif isinstance(field, CollectionField):
                m2m = getattr(model, mapped_name)
                collection = field.Collection()
                collection._from_queryset(m2m.all())
                setattr(self, name, collection)

            elif hasattr(model, mapped_name):
                setattr(self, name, getattr(model, mapped_name))

        self.bound = True

    def _render(self, obj):
        data = {}

        for item, value in obj.iteritems():
            field = [f for f in self._meta.local_fields 
                        if f.name == item][0]
            if not field.render:
                continue
            if hasattr(self, "render_%s_field" % item):
                render_field = getattr(self, "render_%s_field" % item)
                value = render_field(value)
            if isinstance(value, dict):
                # Lets create a new relation
                document = getattr(self, item)
                #value = document._fetch(value)
                #data[item] = value
                if field.inline:
                    # we render the field inline
                    data[item] = document.render()
                else:
                    data[item] = {
                            'rel': 'related',
                            'href': document.uri()}
                    # Also add the identifier fields into the rendered output
                    identifiers = {}
                    for id_field in document._meta.identifier:
                        identifiers[id_field] = getattr(document, id_field)
                    data[item].update(identifiers)
            elif isinstance(value, list):
                # we render a collection
                collection = getattr(self, item)
                data[item] = collection.render()
            else:
                data[item] = value

        return data

    def _save(self):
        data = {}
        obj = self._to_dict()

        for item, value in obj.iteritems():
            field = [f for f in self._meta.local_fields 
                        if f.name == item][0]
            if field.read_only:
                continue
            if hasattr(self, "save_%s_field" % item):
                # We apply a save field
                save_field = getattr(self, "save_%s_field" % item)
                data[item] = save_field()
                continue
            if isinstance(value, dict):
                # Lets follow a relation
                document = getattr(self, item)
                data[item] = document._save()
            elif isinstance(value, list):
                # we dissovle a collection
                collection = getattr(self, item)
                data[item] = []
                for document in collection.collection_set:
                    data[item].append(document._save())
            else:
                data[item] = value

        return data

    def _fetch(self, obj):
        data = {}

        for item, value in obj.iteritems():
            if hasattr(self, "fetch_%s_field" % item):
                fetch_field = getattr(self, "fetch_%s_field" % item)
                value = fetch_field(value)
                # obj[item] = value
            if isinstance(value, dict):
                field = [f for f in self._meta.related_fields
                        if f.name == item][0]
                # Lets create a new relation
                document = field.Document(value, context=self._context)
                data[item] = document._fetch(value)
            elif isinstance(value, list):
                # we fetch a collection
                field = [f for f in self._meta.local_fields
                        if f.name == item][0]
                collection = field.Collection()
                data[item] = []
                Document = collection.document
                for elem in value:
                    document = Document(elem, context=self._context)
                    data[item].append(document._fetch(elem))
            else:
                data[item] = value

        return data

    def _identifier_state(self):
        data = {}
        for elem in self._meta.identifier:
            # if hasattr(self, "fetch_%s_field" % elem):
            #     fetch_field = getattr(self, "fetch_%s_field" % elem)
            #     data[elem] = fetch_field(getattr(self, elem))
            if hasattr(self, "save_%s_field" % elem):
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

    def render(self):
        """Return the document in render state. This includes URI links to
        related resources and the document itself."""
        obj = self._render(self._to_dict())

        return obj

    def to_json(self):
        """Render this document as json."""
        return json.dumps(self.to_python())

    def to_python(self):
        """Render this document to a python dictionary."""
        data = self.render()

        # add the link to itself
        data['link'] = {
                'rel': 'self',
                'href': self.uri()}
        return data

    def validate(self, *args, **kwargs):
        """Validate the state of the document and throw a ``ValidationError``
        if validation fails."""
        errors = {}

        for field in self._meta.local_fields:
            try:
                if (isinstance(getattr(self, field.name), type(None))
                        and field.optional):
                    continue
                elif isinstance(field, ForeignDocument):
                    document = getattr(self, field.name)
                    try:
                        document.validate()
                    except ValidationError, e:
                        if field.optional and not document.bound:
                            continue
                        else:
                            # In cases were want to reference already existing
                            # documents, we will raise an validation error if
                            # we reference the document only by identifier. So
                            # lets fetch it to see if this is the case
                            try:
                                document.fetch(*args, **kwargs)
                                #TODO: I blindly assume now that if a document
                                # is retrieved from the backend it will
                                # validate, so no need to do that again here.
                            except BackendDoesNotExist:
                                raise e
                elif isinstance(field, CollectionField):
                    collection = getattr(self, field.name)
                    for document in collection.collection_set:
                        document.validate()
                else:
                    value = getattr(self, field.name)
                    if ((isinstance(value, type(None))
                            or (isinstance(value, str) and value in ""))
                            and field.optional):
                        # we don't validate optional fields that are not set
                        continue
                    field.clean(value)
            except ValidationError, e:
                errors[field.name] = e.message

        if errors:
            raise ValidationError(errors)

        return True

    def save(self, *args, **kwargs):
        """Save the document to a backend. Any arguments given to this method
        is used when calling the underlying backend method."""
        self.validate(*args, **kwargs)

        self._backend_manager.save(self, *args, **kwargs)

    def update(self, data, *args, **kwargs):
        """Update a document from a dictionary. This is a convenience
        method."""
        self.fetch(*args, **kwargs)

        # First update the own document state with the new values
        self._from_dict(data)

        # save the representation to the model
        self.save(*args, **kwargs)

    def fetch(self, *args, **kwargs):
        """Fetch the model from the backend to create the representation of
        this resource."""
        # Retrieve the object from the backend
        obj = self._backend_manager.fetch(self, *args, **kwargs)
        obj = self._fetch(obj)
        self._from_dict(obj)

    def delete(self, *args, **kwargs):
        """Delete a model instance associated with this document."""
        self._backend_manager.delete(self, *args, **kwargs)

    def uri(self):
        """Return the absolute uri for this resource.

        :return: The URI of this resource.
        :rtype: string

        Implement this method on your document if you have special needs for
        the form of the URI.

        .. note::

            This method should always return the absolute URI as a string.

        """
        if hasattr(self._backend_manager, 'uri'):
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
