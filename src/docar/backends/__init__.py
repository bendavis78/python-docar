import sys

from .django import DjangoBackendManager
from .http import HttpBackendManager


__all__ = ['DjangoBackendManager', 'HttpBackendManager']


class BackendManager(object):
    def __new__(self, backend_type='django'):
        # create the specific backend manager
        mod = sys.modules[__name__]
        Manager = getattr(mod, "%sBackendManager" %
                backend_type.capitalize())

        return Manager()
