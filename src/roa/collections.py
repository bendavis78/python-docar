from documents import Document


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
    def __init__(self, documents=None):
        if not self.document:
            #FIXME: raise and exception, a collection must be bound
            pass
        self.collection_set = []
        for doc in documents:
            self.add(doc)

    def add(self, doc):
        if not isinstance(doc, Document):
            # we only add real documents to the collection set
            return
        else:
            # Append the document
            self.collection_set.append(doc)
