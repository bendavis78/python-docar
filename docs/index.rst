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

A document maps to a resource, whereas it doesn't matter how this resource is
expressed. The resource can be a database model or a HTTP endpoint.
``python-docar`` implements at the moment a backend for django models and a
backend for a http endpoint.

* Each message is declared as a python class that subclasses
  :class:`docar.Document`.
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

.. py:class:: docar.Document

All documents inherit from the :class:`docar.Document` class. It acts as a
representation of a resource. A resource maps to a datastructure that is stored
in a backend, see the section about `Backends`_ for more information. Each
attribute of the document maps to a field of the resource in the backend.

Document methods
----------------

A document exposes a simple API:

.. py:method:: Document.fetch(*args, **kwargs)

Fetch the resource from the backend and bind the document to this resource.

.. py:method:: Document.save(*args, **kwargs)
  
If the document does not exist on the backend, create it. Otherwise update the
existing backend with information stored in the current document.

.. py:method:: Document.delete(*args, **kwargs)
  
Delete the current resource from the backend.

.. py:method:: Document.to_python()
  
Render the document into a python dictionary. The process adds met information
such as the link to itself to the representation.

.. py:method:: Document.to_json()
  
Render the document to a json string. This basically serializes the result from
:meth:`~Document.to_python`.

.. py:method:: Document.uri()

The :meth:`~Document.uri` method returns the resource identifier of this
resource. This method needs to be implemented by the user. It is used to
render the link to itself. The return value of this method should always be the
full location of the resource as a string::

    class Article(Document):
        id = fields.NumberField()

        def uri(self):
            return "http://location/articles/%s/" % self.id

.. py:method:: Document.scaffold()

The :meth:`~Document.scaffold` creates a skeleton of the document. It returns a
python dictionary::

    >>> class Article(Document):
    ...     id = fields.NumberField()
    ...     name = fields.StringField()

    >>> article = Article()
    >>> article.scaffold()
    {
        "id": None,
        "name": ""
    }

``Meta``
--------

.. py:class:: Meta

The behaviour of the document can be controlled by setting attributes on the
document's :class:`Meta` class.

.. code-block:: python

    class Article(Document):
        id = fields.NumberField()
        name = fields.StringField()

        class Meta:
            identifier = 'id'

There are only a few options available at the moment:

.. py:attribute:: Meta.identifier

Specify the field name, that serves as an unique identifier for this document.
The field is specified as a simple string. If you want to use more than one
field as identifiers, write them as a list of strings::

    class Meta:
        identifier = ['id', 'name']

Every document needs to specify an identifer. Every resource should be uniquely
selectable by the value of those fields. The default identifier is named ``id``.

.. py:attribute:: Meta.backend_type

Choose the backend this document should connect to. See the section about
`Backends`_ below for details. The default backend is the `Django backend`_.

.. py:attribute:: Meta.model

This option is only useful for documents connecting to the `Django Backend`_.
It takes a class as argument and specifies which django model use. The argument
must be a class and **can't** be a string::

    from djangoapp.models import ArticleModel

    class Article(Document):
        id = fields.NumberField()

        class Meta:
            model = ArticleModel


Fields
======

Documents declare their attributes using fields set as class attributes. The
name of a field maps straight to the name of a field of the underlying
resource. See `Map Fields`_ for a way to use a different field name for the
document and the resource.

Example

.. code-block:: python

    class Message(Document):
        id = fields.NumberField()
        name = fields.StringField()

Field Options
-------------

``optional``
~~~~~~~~~~~~

.. py:attribute:: Field.optional

When set to ``True``, This field can be optional and will be ignored if not set
to a value. Default is ``False``.

``default``
~~~~~~~~~~~

.. py:attribute:: Field.default

Specify a default value for this field. If no value is set by the user, the
default value is used when interacting with the backend.

``scaffold``
~~~~~~~~~~~~

.. py:attribute:: Fields.scaffold

Control whether to scaffold this field. Defaults to ``True``.

Field Types
-----------

``NumberField``
~~~~~~~~~~~~~~~

.. py:class:: NumberField(**options)

``StringField``
~~~~~~~~~~~~~~~

.. py:class:: StringField(**options)

``BooleanField``
~~~~~~~~~~~~~~~~

.. py:class:: BooleanField(**options)

``StaticField``
~~~~~~~~~~~~~~~

.. py:class:: StaticField(**options)

``ForeignDocument``
~~~~~~~~~~~~~~~~~~~

.. py:class:: ForeignDocument(**options)

``CollectionField``
~~~~~~~~~~~~~~~~~~~

.. py:class:: CollectionField(**options)

Map Fields
----------

You can map a field name between the document and the underlying resource by
implementing a :meth:`map_FIELD_field` method where ``FIELD`` is the name of
the document field. The method returns a string with the actual name of the
resource field.

.. code-block:: python

    # We define a simple django model
    class ArticleModel(models.Model):
        long_title = models.CharField(max_length=200)

    # We define a document where we want to use name as a field name instead of
    # long_title
    class Article(Document):
        id = fields.NumberField()
        name = fields.StringField()

        class Meta:
            backend_type = 'django'
            model = ArticleModel

        map_name_field(self):
            return "long_title"

In the above example the document defines a field ``name``. For any operation
with the underlying resource, it will map ``name`` to ``long_title``.

``fetch_FIELD_field``

``render_FIELD_field``

``save_FIELD_field``

Collections
===========

Backends
========

The backends are the real meat of the documents. Where the document defines what
you can do, the backends implement the how of it. 

HTTP Backend
------------

The HTTP backend uses the ``requests`` library to communicate to remote
backends over HTTP. It assumes currently JSON as exchange protocol. The
document methods map the following way to the HTTP backend:

- :meth:`~Document.fetch` --> HTTP GET
- :meth:`~Document.save` --> HTTP POST (on create)
- :meth:`~Document.save` --> HTTP PUT (on update)
- :meth:`~Document.delete` --> HTTP DELET

uri methods
~~~~~~~~~~~

This backend uses the :meth:`~Document.uri` method to determine its API
endpoint. You can implement specific uri methods for each HTTP verb to be more
precise. If a http specific uri method is not found, it will fallback to the
default :meth:`~Document.uri` method. The form of those methods is
``verb_uri``::

    class Article(Document):
        id = fields.NumberField()

        def post_uri(self):
            # Use this method for POST requests
            return "http://post_location"

        def uri(self):
            # The default uri location for all other HTTP requests
            return "http://location"

Django Backend
--------------

The django backend stores and retrieves resources using the `Django ORM`_.

.. _`Django ORM`: http://djangoproject.org

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

