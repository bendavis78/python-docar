import unittest

from nose.tools import eq_, ok_

from docar.models import ModelManager, DjangoModelManager


class when_a_model_manager_gets_instantiated(unittest.TestCase):
    def it_takes_the_model_type_as_an_argument(self):
        manager = ModelManager('django')
        eq_('django', manager.model_type)

    def it_defaults_to_the_django_model_type(self):
        manager = ModelManager()
        eq_('django', manager.model_type)

    def it_abstracts_a_specific_model_manager(self):
        manager = ModelManager('django')
        ok_(isinstance(manager._manager, DjangoModelManager))


