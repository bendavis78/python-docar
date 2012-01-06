import sys


class ModelManager(object):
    def __init__(self, model_type='django'):
        self.model_type = model_type

        # create the specific model manager
        mod = sys.modules[__name__]
        Manager = getattr(mod, "%sModelManager" %
                self.model_type.capitalize())

        self._manager = Manager()

    def fetch(self, *args, **kwargs):
        # A stub, call the specific model manager method
        return self._manager.fetch(*args, **kwargs)

    def save(self, *args, **kwargs):
        # A stub, call the specific model manager method
        return self._manager.save(*args, **kwargs)


class DjangoModelManager(object):
    def fetch(self, *args, **kwargs):
        pass

    def save(self, *args, **kwargs):
        pass
