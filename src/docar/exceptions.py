class BackendDoesNotExist(Exception):
    """Throw this error if the document tries to fetch from a backend and the
    model is not found."""
    pass


class AmbigiousModelMapping(Exception):
    """The document couldn't be mapped unambigiously to a model."""
    pass


class CollectionNotBound(Exception):
    """A collection hasn't been bound to a document."""
    pass


class HttpBackendError(Exception):
    """A request from the HTTP backend returned a status code >400 and <500."""
    pass
