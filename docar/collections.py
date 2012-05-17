import json

from .documents import Document
from .exceptions import CollectionNotBound


class Collection(object):
    """A collection is a container for a list of documents.

    In JSON terms this would be the structural datatype ``Array``. It provides
    methods to manipulate the collection. The collection itself is stored as a
    list. A collection always has to be mapped to a document. You can do hat by
    declaring the ``document`` class variable upon declaration of this class.

    Upon instantiation you can provide a list of documents to add to the
    collection set.

    :param documents: A list of documents.
    :type documents: Document

    """
    document = None
    bound = False
    _context = {}

    def __init__(self, documents=None):
        if not self.document:
            # A collection must declared for a document
            raise CollectionNotBound

        self.collection_set = []
        if documents:
            # Add the supplied documents to the collection
            for doc in documents:
                self.add(doc)

    def add(self, doc):
        if not isinstance(doc, Document):
            # we only add real documents to the collection set
            return
        else:
            # Append the document
            self.collection_set.append(doc)
            self.bound = True

    def delete(self, identifier):
        """Delete a document from the collection. Use a dict to specify the
        right document."""
        new_collection = []
        for doc in self.collection_set:
            doc_id = doc._identifier_state()
            for k, v in identifier.iteritems():
                if v != doc_id[k]:
                    new_collection.append(doc)

        self.collection_set = new_collection
        if len(self.collection_set) < 1:
            self.bound=False

    def fetch_all(self, query_list=[]):
        # FIXME: Make this a method to run a fetch command on all documents in
        # the collection set
        for item in query_list:
            doc = self.document(item)
            doc.fetch()
            self.add(doc)

    def _render(self):
        data = []
        for document in self.collection_set:
            item = {"rel": "item"}

            #FIXME: Design decision needed, if I enable this, I get into
            # troubles when rendering related (m2m) instances and they lack the
            # parent instance as select field.
            #document.fetch()
            item["href"] = document.uri()
            for elem in document._meta.identifier:
                item[elem] = getattr(document, elem)
            data.append(item)

        return data

    def render(self):
        data = {
                'size': len(self.collection_set),
                }
        items = []

        for document in self.collection_set:
            item = document.to_python()
            #we change the relation attribute of this document
            if 'link' in item:
                item['link']['rel'] = 'item'
            items.append(item)

        data['items'] = items

        return data

    def _to_dict(self):
        data = []
        for document in self.collection_set:
            data.append(document._to_dict())

        return data

    def to_python(self):
        data = self.render()

        if hasattr(self, 'uri'):
            data['link'] = {
                'rel': 'self',
                'href': self.uri()
                }

        return data

    def to_json(self):
        return json.dumps(self._render())
