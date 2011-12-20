from mock import Mock

from roa import Collection
from roa import Document
from roa import fields


ArticleModel = Mock(name='ArticleModel')
ArticleModel.DoesNotExist = Exception

class Article(Document):
    id = fields.NumberField()
    name = fields.StringField()

    class Meta:
        model = ArticleModel


class NewsPaper(Collection):
    document = Article
