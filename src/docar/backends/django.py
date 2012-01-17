from docar.exceptions import BackendDoesNotExist


class DjangoBackendManager(object):
    backend_type = 'django'

    def fetch(self, document):
        state = document._identifier_state()
        try:
            instance = self._model.objects.get(**state)
        except self._model.DoesNotExist:
            raise BackendDoesNotExist("Fetch failed for %s" % str(self._model))

        self.instance = instance

        return instance

    def _get_collection(self, field):
        # FIXME: This relies on the fact that fetch has been called already
        instance = self.instance

        # create a new collection first
        collection = field.Collection()

        # create a document for each item in the m2m relation
        relation = getattr(instance, field.name)
        for item in relation.all():
            doc = collection.document()
            for elem in doc._meta.identifier:
                setattr(doc, elem, getattr(item, elem))
            collection.add(doc)
        return collection

    def save(self, document):
        select_dict = document._identifier_state()
        m2m_relations = []

        # we run this method to make sure we catch all save_FIELD_field methods
        doc_state = document._save_state()

        for field in document._meta.local_fields:
            if hasattr(field, 'Collection'):
                m2m_relations.append((field, getattr(document, field.name)))
                # we deal with collections later
                break
            elif hasattr(field, 'Document'):
                # a foreign document means we have to retrieve it from the
                # model
                doc = getattr(document, field.name)
                try:
                    instance = doc.fetch()
                except BackendDoesNotExist:
                    #FIXME: make sure it doesn't throw an exception
                    doc.save()
                    instance = doc._backend_manager.instance
                select_dict[field.name] = instance
            # Add the value to the select_dict only if its not None
            elif getattr(document, field.name) or field.default == False:
                # update the dict with the value from the document state
                select_dict[field.name] = doc_state[field.name]

        # add the additional context in retrieving the model instance
        select_dict.update(document._context)

        # First try to retrieve the existing model if it exists
        instance, created = self._model.objects.get_or_create(**select_dict)
        #instance.save()

        # instance can be used to set the m2m relations
        for item in m2m_relations:
            m2m = getattr(instance, item[0].name)
            for doc in item[1].collection_set:
                # FIXME: Replace get_or_create with a more fine grained control
                # to be able to retrieve instances only with the identifier?
                m2m.get_or_create(**doc._save_state())

        self.instance = instance

    def delete(self, document):
        try:
            # First try to retrieve the existing model if it exists
            instance = self.fetch(document)
        except BackendDoesNotExist:
            # In case the model does not exist, we do nothing
            return

        instance.delete()

    def uri(self):
        return self.instance.get_absolute_url()