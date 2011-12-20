from roa import Collection
from roa import Document
from roa import fields


class Article(Document):
    id = fields.NumberField()
    name = fields.StringField()

    class Meta:
        model = 'Article'


class NewsPaper(Collection):
    document = Article
