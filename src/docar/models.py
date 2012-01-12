import sys

from .exceptions import ModelDoesNotExist


class ModelManager(object):
    def __new__(self, model_type='django'):
        # create the specific model manager
        mod = sys.modules[__name__]
        Manager = getattr(mod, "%sModelManager" %
                model_type.capitalize())

        return Manager()


class DjangoModelManager(object):
    model_type = 'django'

    def fetch(self, *args, **kwargs):
        try:
            instance = self._model.objects.get(**kwargs)
        except self._model.DoesNotExist:
            raise ModelDoesNotExist("Fetch failed for %s" % str(self._model))

        self.instance = instance
        return instance

    def _get_collection(self, field):
        # FIXME: Tis relies on the fact that fetch has been called already
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
        select_dict = {}
        m2m_relations = []

        # we run this method to make sure we catch all save_FIELD_field methods
        doc_state = document._get_document_state()

        #FIXME: Whats with foreign relations?
        #for elem, value in document._get_document_state().iteritems():
        for field in document._meta.local_fields:
            if hasattr(field, 'Collection'):
                m2m_relations.append((field, getattr(document, field.name)))
                # we deal with collections later
                break
            # update the dict with the value from the document state
            select_dict[field.name] = doc_state[field.name]

        # First try to retrieve the existing model if it exists
        instance = self._model.objects.get_or_create(**select_dict)

        # instance can be used to set the m2m relations
        for item in m2m_relations:
            m2m = getattr(instance, item[0].name)
            for doc in item[1].collection_set:
                m2m.get_or_create(**doc._get_document_state())

    def delete(self, identifier, *args, **kwargs):
        select_dict = {}
        for elem in identifier:
            select_dict[elem] = kwargs[elem]

        try:
            # First try to retrieve the existing model if it exists
            instance = self._model.objects.get(**select_dict)
        except self._model.DoesNotExist:
            # In case the model does not exist, we do nothing
            return

        instance.delete()

    def uri(self):
        return self.instance.get_absolute_url()
