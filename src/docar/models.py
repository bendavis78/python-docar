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

    def save(self, identifier, *args, **kwargs):
        select_dict = {}
        for elem in identifier:
            select_dict[elem] = kwargs[elem]

        #FIXME: Use get_or_create() manager method
        try:
            # First try to retrieve the existing model if it exists
            instance = self._model.objects.get(**select_dict)
        except self._model.DoesNotExist:
            # if not we are creating a new model
            instance = self._model(**kwargs)

        #FIXME: Whats with foreign relations?
        for elem, value in kwargs.iteritems():
            setattr(instance, elem, value)

        instance.save()

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
