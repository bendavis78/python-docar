import sys

from .django import DjangoBackendManager


__all__ = ['DjangoBackendManager']


class BackendManager(object):
    def __new__(self, backend_type='django'):
        # create the specific backend manager
        mod = sys.modules[__name__]
        Manager = getattr(mod, "%sBackendManager" %
                backend_type.capitalize())

        return Manager()
