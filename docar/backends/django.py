from docar.exceptions import BackendDoesNotExist
from docar.fields import ForeignDocument, CollectionField

class DjangoBackendManager(object):
    backend_type = 'django'

    def _to_dict(self, document):
        if not self.instance:
            #FIXME: Handle not fetched instances better
            return {}
        data = {}
        instance = self.instance
        for field in document._meta.local_fields:
            # copy to field name to be able to map it in the process
            instance_field_name = field.name
            if hasattr(document, "map_%s_field" % field.name):
                # We map the fieldname of the backend instance to the fieldname
                # of the document.
                map_field = getattr(document, "map_%s_field" % field.name)
                # just create a new field on the instance itself
                instance_field_name = map_field()
            if not hasattr(instance, instance_field_name):
                # The instance has no value for this field
                data[field.name] = None
                continue
            if isinstance(field, ForeignDocument):
                kwargs = {}
                related_instance = getattr(instance, instance_field_name)

                if not related_instance:
                    # The related instance is not set. We ignore if a related
                    # instance does not exist otherwise we raise
                    # model.DoesNotExist exception later on.
                    continue

                Document = field.Document
                for identifier in Document._meta.identifier:
                    kwargs[identifier] = getattr(related_instance, identifier)
                doc = Document(kwargs, document._context)
                # To avoid a new fetch, set the instance manualy, needed for
                # the uri method
                doc._backend_manager.instance = related_instance
                doc.bound = True
                data[field.name] = doc._backend_manager._to_dict(doc)
            elif isinstance(field, CollectionField):
                data[field.name] = self._get_collection(field, instance_field_name,
                        context=document._get_context())
            elif hasattr(instance, instance_field_name):
                # Otherwise set the value of the field from the retrieved model
                # object
                data[field.name] = getattr(instance, instance_field_name)

        return data

    def _get_collection(self, field, instance_field_name, context={}):
        # FIXME: This relies on the fact that fetch has been called already
        instance = self.instance

        # create a new collection first
        collection = field.Collection()

        # create a document for each item in the m2m relation
        relation = getattr(instance, instance_field_name)

        for item in relation.all():
            # we first create an empty document
            doc = collection.document({}, context=context)

            # We dont need to fetch the object again
            doc._backend_manager.instance = item

            # we shortcut here the fetch mechanism, turn it into a dict
            # representation on set the attributes correctly
            obj = doc._backend_manager._to_dict(doc)
            obj = doc._fetch(obj)
            doc._from_dict(obj)

            collection.add(doc)

        return collection._to_dict()

    def fetch(self, document, *args, **kwargs):
        select_dict = document._identifier_state()
        select_dict.update(document._get_context())

        try:
            instance = self._model.objects.get(**select_dict)
        except self._model.DoesNotExist:
            raise BackendDoesNotExist("Fetch failed for %s" % str(self._model))

        self.instance = instance

        return self._to_dict(document)

    def save(self, document, *args, **kwargs):
        m2m_relations = []

        # we call this method to make sure we run all save_FIELD_field methods
        doc_state = document._save()

        # we defere the collections to later and replace foreign documents with
        # foreign related model instances
        for field in document._meta.local_fields:
            # we make a copy of the name, to not interfere with other documents
            # when saving them
            name = field.name
            if hasattr(document, "map_%s_field" % field.name):
                # we map the attribute name
                map_field = getattr(document, "map_%s_field" % field.name)
                doc_state[map_field()] = getattr(document, field.name)
                name = map_field()
                setattr(document, name, doc_state[name])
            if hasattr(field, 'Collection'):
                # we defer m2m relationships to later, we need the field, the
                # name of the field (after the map() method) and the actual m2m
                # relation
                m2m_relations.append((field, name, getattr(document, name)))
                # and remove it from the state dict to not save it now
                del(doc_state[name])
            elif hasattr(field, 'Document'):
                # a foreign document means we have to retrieve it from the
                # model
                doc = getattr(document, name)
                # Don't try to save or fetch if the document isn't bound,
                # won't do us any good.
                try:
                    doc.fetch()
                except BackendDoesNotExist:
                    #FIXME: make sure it doesn't throw an exception
                    if field.optional and not doc.bound:
                        continue
                    else:
                        doc.save()

                instance = doc._backend_manager.instance
                doc_state[name] = instance

        # add the additional context in retrieving the model instance
        doc_state.update(document._get_context())
        select_dict = document._identifier_state()
        select_dict.update(document._get_context())

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

        self.instance = instance

        # Save the m2m relations
        self._save_m2m_relations(instance, m2m_relations)

    def _save_m2m_relations(self, instance, m2m_relations):
        # set the m2m relations
        defered_m2m = []
        for field, local_name, collection in m2m_relations:
            if len(collection.collection_set) < 1:
                continue
            m2m = getattr(instance, local_name)
            for doc in collection.collection_set:
                doc_state = doc._save()

                # Iterate all fields of this doc, to defere collections
                for field in doc._meta.local_fields:
                    defered_name = field.name
                    if hasattr(doc, "map_%s_field" % defered_name):
                        # we map the attribute name
                        map_field = getattr(doc,
                                "map_%s_field" % defered_name)
                        doc_state[map_field()] = getattr(doc, defered_name)
                        del(doc_state[defered_name])
                        defered_name = map_field()
                        setattr(doc, defered_name, doc_state[defered_name])
                    if hasattr(field, 'Collection'):
                        # we defere nested m2m relationships to later, filter
                        # them out here to deal with it on a later point
                        defered_m2m.append((field, defered_name, getattr(doc,
                            defered_name)))
                        del(doc_state[defered_name])
                    elif (hasattr(field, 'Document')
                            and defered_name in doc_state):
                        document = field.Document(doc_state[defered_name])
                        document.save()
                        doc_state[defered_name] = document._backend_manager.instance

                # create or update the relation object
                model = m2m.__dict__['model']
                try:
                    inst = m2m.get(**doc._identifier_state())
                    for k, v in doc_state.items():
                        setattr(inst, k, v)
                    inst.save()
                except model.DoesNotExist:
                    inst = m2m.create(**doc_state)

                # now recursively add the nested collections
                if len(defered_m2m) > 0:
                    self._save_m2m_relations(inst, defered_m2m)

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
