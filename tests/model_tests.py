import unittest

from nose.tools import eq_, ok_
from mock import patch, Mock

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

    def it_can_fetch_and_save_to_the_specific_model_manager(self):
        with patch('docar.models.DjangoModelManager') as mock:
            mock_manager = Mock()
            mock_manager = mock.return_value
            manager = ModelManager('django')
            # first assert that the manager is really mocked
            ok_(isinstance(manager._manager, Mock))
            manager.fetch()
            manager.save()
            eq_(True, mock_manager.fetch.called)
            eq_(True, mock_manager.save.called)
