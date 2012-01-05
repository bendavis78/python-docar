class ModelDoesNotExist(Exception):
    """Throw this error if the document tries to fetch a non existing model."""
    pass


class AmbigiousModelMapping(Exception):
    """The document couldn't be mapped unambigiously to a model."""
    pass
