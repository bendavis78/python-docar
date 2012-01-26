from docar.exceptions import BackendDoesNotExist
from docar.fields import ForeignDocument, CollectionField


class DjangoBackendManager(object):
    backend_type = 'django'

    def _model_to_document_dict(self, document):
        instance = self.instance
        data = {}
        for field in document._meta.local_fields:
            if hasattr(document, "fetch_%s_field" % field.name):
                # We map the fieldname of the backend instance to the fieldname
                # of the document.
                fetch_field = getattr(document, "fetch_%s_field" % field.name)
                # just create a new field on the instance itself
                setattr(instance, field.name, getattr(instance, fetch_field()))
            if not hasattr(instance, field.name):
                # The instance has no value for this field
                data[field.name] = None
                continue
            if isinstance(field, ForeignDocument):
                kwargs = {}
                related_instance = getattr(instance, field.name)
                Document = field.Document
                for identifier in Document._meta.identifier:
                    kwargs[identifier] = getattr(related_instance, identifier)
                doc = Document(kwargs)
                # To avoid a new fetch, set the instance manualy, needed for
                # the uri method
                doc._backend_manager.instance = related_instance
                data[field.name] = doc
            elif isinstance(field, CollectionField):
                data[field.name] = self._get_collection(field)
            elif hasattr(instance, field.name):
                # Otherwise set the value of the field from the retrieved model
                # object
                data[field.name] = getattr(instance, field.name)

        return data

    def _get_collection(self, field):
        # FIXME: This relies on the fact that fetch has been called already
        instance = self.instance

        # create a new collection first
        collection = field.Collection()

        # create a document for each item in the m2m relation
        relation = getattr(instance, field.name)

        for item in relation.all():
            select_dict = {}
            for elem in collection.document._meta.identifier:
                select_dict[elem] = getattr(item, elem)
            doc = collection.document(select_dict)
            collection.add(doc)
        return collection

    def fetch(self, document, **kwargs):
        select_dict = document._identifier_state()
        select_dict.update(document._context)

        try:
            instance = self._model.objects.get(**select_dict)
        except self._model.DoesNotExist:
            raise BackendDoesNotExist("Fetch failed for %s" % str(self._model))

        self.instance = instance

        #return instance
        return self._model_to_document_dict(document)

    def save(self, document, **kwargs):
        #select_dict = document._identifier_state()
        m2m_relations = []

        # we run this method to make sure we catch all save_FIELD_field methods
        doc_state = document._prepare_save()

        # we defere the collections to later and replace foreign documents with
        # foreign related model instances
        for field in document._meta.local_fields:
            if hasattr(document, "fetch_%s_field" % field.name):
                # we map the attribute name
                fetch_field = getattr(document, "fetch_%s_field" % field.name)
                doc_state[fetch_field()] = getattr(document, field.name)
                field.name = fetch_field()
                setattr(document, field.name, doc_state[field.name])
            if hasattr(field, 'Collection'):
                # we defere m2m relationships to later
                m2m_relations.append((field, getattr(document, field.name)))
                del(doc_state[field.name])
            elif hasattr(field, 'Document'):
                # a foreign document means we have to retrieve it from the
                # model
                doc = getattr(document, field.name)
                try:
                    doc.fetch()
                except BackendDoesNotExist:
                    #FIXME: make sure it doesn't throw an exception
                    doc.save()

                instance = doc._backend_manager.instance
                doc_state[field.name] = instance

        # add the additional context in retrieving the model instance
        doc_state.update(document._context)
        select_dict = document._identifier_state()
        select_dict.update(document._context)

        # First try to retrieve the existing model if it exists
        try:
            instance = self._model.objects.get(**select_dict)
        except self._model.DoesNotExist:
            # We create a new model instance
            instance = self._model(**select_dict)

        # Set the new state for the model instance
        for k, v in doc_state.iteritems():
            setattr(instance, k, v)

        # save the model to the backend
        #FIXME: Do some exception handling, maybe a full_clean first
        instance.save()

        # set the m2m relations
        for item in m2m_relations:
            m2m = getattr(instance, item[0].name)
            for doc in item[1].collection_set:
                # FIXME: Replace get_or_create with a more fine grained control
                # to be able to retrieve instances only with the identifier?
                #doc.save()
                m2m.get_or_create(**doc._prepare_save())
                #m2m.add(doc._backend_manager.instance)

        self.instance = instance

    def delete(self, document, **kwargs):
        try:
            # First try to retrieve the existing model if it exists
            self.fetch(document)
        except BackendDoesNotExist:
            # In case the model does not exist, we do nothing
            return

        self.instance.delete()

    def uri(self):
        return self.instance.get_absolute_url()
