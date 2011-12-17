import unittest

from nose.tools import eq_

from roa.documents import Document


class ExampleDocument(Document):
    pass


class when_a_document_gets_instantiated(unittest.TestCase):
    def setUp(self):
        self.doc = ExampleDocument()

    def it_has_a_to_json_method(self):
        #print dir(self)
        eq_(True, hasattr(self.doc, 'to_json'))
