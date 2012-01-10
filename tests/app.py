from mock import Mock

from docar import Collection
from docar import Document
from docar import fields


EditorModel = Mock(name='EditorModel')
EditorModel.DoesNotExist = Exception

ArticleModel = Mock(name='ArticleModel')
ArticleModel.DoesNotExist = Exception

TagModel = Mock(name='TagModel')
TagModel.DoesNotExist = Exception


class Editor(Document):
    first_name = fields.StringField()
    last_name = fields.StringField()
    age = fields.NumberField()

    class Meta:
        model = EditorModel
        identifier = [
                'first_name',
                'last_name']


class Tag(Document):
    slug = fields.StringField()

    class Meta:
        model = TagModel
        identifier = 'slug'


class TagCloud(Collection):
    document = Tag


class Article(Document):
    id = fields.NumberField()
    name = fields.StringField()
    tags = fields.CollectionField(TagCloud)
    editor = fields.ForeignDocument(Editor)
    #published = fields.ChoiceField(choices=PUBLISH_CHOICES)

    class Meta:
        model = ArticleModel


class NewsPaper(Collection):
    document = Article
