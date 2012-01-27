.. python-docar documentation master file, created by
   sphinx-quickstart on Sat Dec 17 18:44:13 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

========================================
Welcome to python-docar's documentation!
========================================

A lot of web services provide nowadays a REST interface and clients can
communicate and manipulate state on the server by exchanging messages.
``python-docar`` provides a declarative style of defining those messages as
documents, and makes it possible to resue the definitions on the server as well
as on the client side. 

On the server those messages map to a model. At the moment this means a django
model, but support for other model mappers is planned. On the client messages
can be generated and send right away in the form of a HTTP request with the
HTTP backend.

* Each message is declared as a python class that subclasses
  :class:`docar.documents.Document`.
* Each attribute of the document represents one field in the message.
* Other documents can be referenced and handled inline.
* More than one document of the same type are handled in collections.
* You can reuse the same document declarations and only replace the backend.

A quick example
===============

.. code-block:: python

    >>> # The document declaration
    >>> from docar import Document, fields
    >>> from djangoproject.newspaper import ArticleModel

    >>> class Article(Document):
    ...     id = fields.NumberField()
    ...     name = fields.StringField()
    ...
    ...     class Meta:
    ...         backend_type = 'django'
    ...         model = ArticleModel

    >>> # A server example
    >>> article = Article({'id': 1})
    >>> article.fetch()  # Fetch this document from the backend
    >>> article.to_json()
    {
        "id": 1,
        "name": "Headline",
        "link": {
            "rel": "self",
            "href": "http://example.org/article/1/"
        }
    }

    >>> article.headline = "Another Headline"
    >>> article.save()  # Save the document to the backend model
    >>> article.to_json()
    {
        "id": 1,
        "name": "Another Headline",
        "link": {
            "rel": "self",
            "href": "http://example.org/article/1/"
        }
    }

    >>> # A client example
    >>> article = Article()
    >>> article.name = "Next Headline"
    >>> article.create()
    <class 'docar.http.HttpResponse'>

    >>> # You can also declare a collection of documents
    >>> from docar import Collection
    >>> class NewsPaper(Collection):
    ...     document = Article

    >>> newspaper = NewsPaper()
    >>> newspaper.add(article)
    >>> newspaper.to_json()
    [{
        "id": 1,
        "headline": "Headline"
        "link": {
            "rel": "self",
            "href": "http://example.org/article/1/"
        }
    }]

Documents
=========

Fields
======

Documents declare their attributes using fields set as class attributes.

Example

.. code-block:: python

    class Message(Document):
        id = fields.NumberField()
        name = fields.StringField()

Field Options
-------------

``optional``
~~~~~~~~~~~~

.. attribute:: Field.optional

When set to ``True``, This field can be optional and will be ignored if not set
to a value. Default is ``False``.

``default``
~~~~~~~~~~~

.. attribute:: Field.default

Specify a default value for this field. If no value is set by the user, the
default value is used when interacting with the backend.

Field Types
-----------

``NumberField``
~~~~~~~~~~~~~~~

.. class:: NumberField(**options)

``StringField``
~~~~~~~~~~~~~~~

.. class:: StringField(**options)

``BooleanField``
~~~~~~~~~~~~~~~~

.. class:: BooleanField(**options)

``StaticField``
~~~~~~~~~~~~~~~

.. class:: StaticField(**options)

``ForeignDocument``
~~~~~~~~~~~~~~~~~~~

.. class:: ForeignDocument(**options)

``CollectionField``
~~~~~~~~~~~~~~~~~~~

.. class:: StaticField(**options)

Collections
===========

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

