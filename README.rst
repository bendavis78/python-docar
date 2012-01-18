============
python-docar
============

``python-docar`` gives an declarative syntax for defining messages passed
between client and server applications. By moving the focus of web applications
to the documents exchanged it gives you the possibility to implement document
oriented architectures. In this way you can map documents (messages) to
resources identified by URI's. The target applications are web apps that
implement a RESTful interface.

On the server side those documents can be mapped to an underlying model store.
At this time the django-orm mapper is supported. But ``python-docar`` is not
really reduced to django. Other model mappers like sqlalchemy-orm or a mongodb
mapper are possible.

The same document definitions can be reused on the client side. In the future
it will come with a http client that can craft messages and send them right
away to the server applications.

In the future those declarations should be able to enforce validation on those
documents. That means, that on the client you can validate the message prior to
sending the HTTP request and on the server prior to saving the resource to the
data store.

At the moment the only messaging format supported is a very simple JSON format.
It is planned to provide more dialects (like xml) or the possibility to
override the builtin serializers.

``python-docar`` is heavily influenced by roar_.

.. _roar: https://github.com/apotonick/roar

Example
=======

The following code is a simplified example of how to use ``python-docar``. We
start using the django backend::

    # First declare your document
    from webapp.models import EntryModel, AuthorModel
    from docar import Document, Collection, fields

    class Author(Document):
        name = fields.StringField()

        class Meta:
            backend_type = 'django'
            model = AuthorModel
            identifier = 'name'
        
    class BlogEntry(Document):
        id = fields.NumberField()
        title = fields.StringField()
        body = fields.StringField()
        published = fields.BooleanField(default=False)
        author = fields.ForeignDocument(Author)

        class Meta:
            backend_type = 'django'
            model = EntryModel
            model_type = 'django'  # The default atm
            #identifier = 'id'  # The identifier defaults to 'id'

    # You can also declare collections of documents
    class Blog(Collection):
        document = BlogEntry

You can use those documents in the views of your app::

    from webapp.documents import Author, BlogEntry, Blog

    entry = BlogEntry({'id': 1})

    # Bind the document to a model
    entry.fetch()

I can also change attributes of the document and save it back to the model::

    entry.title = "Hello World"
    entry.save()  # --> saves to the django model backend

The ``to_json`` method renders the document into a json message. It adds a few
goodies to be a better REST player, like the link to itself. It could look like
that::

    # render the document as a json string
    entry.to_json()

    {
        "id": 1,
        "title": "Hello World",
        "body": "Long Text",
        "published": True,
        "author": {
            "rel": "related",
            "href": "https://example.org/author/crito/"
            },
        "link": {
            "rel": "self",
            "href": "https://example.org/entry/1/"
            }
    }

There is another backend in development, that connects documents to a remote
HTTP endpoint. The API is the same, only the underlying backend type differs.
This can be used for client applications to connect to remote services using
the same document declarations.

Installation
============

Clone yourself the latest source from github. Development happens fast, so its
good to always go with the latest commit::

    $ git clone git://github.com/30loops/python-docar.git
    $ cd python-docar
    $ sudo python setup.py install

Development
===========

This module comes along with a thorough test suite. Run it the following way::

    $ cd python-docar
    $ python setup.py nosetests
