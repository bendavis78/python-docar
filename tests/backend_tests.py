import unittest

from nose.tools import eq_, ok_
from mock import Mock

from docar.backends import BackendManager, DjangoBackendManager, \
    HttpBackendManager
from docar import Document, Collection, fields


class when_a_backend_manager_gets_instantiated(unittest.TestCase):
    def it_can_provide_a_link_using_the_django_model(self):
        mock_model = Mock()
        mock_model.get_absolute_url.return_value = "link"

        manager = BackendManager('django')
        manager.instance = mock_model

        eq_("link", manager.uri())
        eq_(True, mock_model.get_absolute_url.called)

    def it_takes_the_backend_type_as_an_argument(self):
        manager = BackendManager('django')
        eq_('django', manager.backend_type)

    def it_defaults_to_the_django_backend_type(self):
        manager = BackendManager()
        eq_('django', manager.backend_type)

    def it_abstracts_a_specific_backend_manager(self):
        manager = BackendManager('django')
        ok_(isinstance(manager, DjangoBackendManager))

        manager = BackendManager('http')
        ok_(isinstance(manager, HttpBackendManager))

    def it_can_specify_the_backend_type_as_a_meta_option(self):
        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'django'
                model = Mock()

        doc = Doc()
        ok_(isinstance(doc._backend_manager, DjangoBackendManager))

        class Doc(Document):
            id = fields.NumberField()

            class Meta:
                backend_type = 'http'

        doc = Doc()
        ok_(isinstance(doc._backend_manager, HttpBackendManager))


