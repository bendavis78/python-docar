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
        ok_(isinstance(manager, DjangoModelManager))

    def it_can_fetch_save_and_delete_to_the_specific_model_manager(self):
        with patch('docar.models.DjangoModelManager') as mock:
            mock_manager = Mock()
            mock_manager = mock.return_value
            manager = ModelManager('django')
            # first assert that the manager is really mocked
            ok_(isinstance(manager, Mock))
            manager.fetch()
            manager.save()
            manager.delete()
            eq_(True, mock_manager.fetch.called)
            eq_(True, mock_manager.save.called)
            eq_(True, mock_manager.delete.called)

    def it_can_fetch_data_from_the_underlying_model(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        DjangoModel.objects.get.return_value = mock_model

        manager = ModelManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoModelManager, type(manager))
        eq_(mock_model, manager.fetch(id=1))
        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)

    def it_can_save_data_to_the_underlying_model(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        DjangoModel.objects.get.return_value = mock_model

        manager = ModelManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoModelManager, type(manager))

        # the manager.save() method doesn't return on success
        manager.save(['id'], id=1)
        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)

    def it_can_delete_the_underlying_model_instance(self):
        DjangoModel = Mock(name="DjangoModel")
        mock_model = Mock()
        DjangoModel.objects.get.return_value = mock_model

        manager = ModelManager('django')
        # The manager needs to know which model it connects to
        # This is normally done when the Document is created.
        manager._model = DjangoModel

        # make sure we are working with correct expectations
        eq_(DjangoModelManager, type(manager))

        manager.delete(['id'], id=1)

        eq_([('objects.get', {'id': 1})], DjangoModel.method_calls)
        eq_([('delete',)], mock_model.method_calls)
