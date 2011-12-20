from documents import Document


class Collection(object):
    def __init__(self, _documents=None):
        if not self.document:
            #FIXME: raise and exception, a collection must be bound
            pass
        self.collection_set = []
        for doc in _documents:
            self.add(doc)

    def add(self, doc):
        if not isinstance(doc, Document):
            # we only add real documents to the collection set
            return
        else:
            # Append the document
            self.collection_set.append(doc)
