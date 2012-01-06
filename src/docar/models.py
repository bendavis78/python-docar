import sys


class ModelManager(object):
    def __init__(self, model_type='django'):
        self.model_type = model_type

        # create the specific model manager
        mod = sys.modules[__name__]
        Manager = getattr(mod, "%sModelManager" %
                self.model_type.capitalize())

        self._manager = Manager()


class DjangoModelManager(object):
    pass
