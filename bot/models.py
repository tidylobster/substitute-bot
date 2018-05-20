# coding: utf-8
from peewee import *

database = SqliteDatabase('substitute.db')


class BaseModel(Model):
    class Meta:
        database = database


class Group(BaseModel):
    class Meta:
        indexes = (
            (('chat', 'name'), True),
        )

    user = IntegerField()
    chat = IntegerField()
    name = CharField(max_length=32)


class GroupUsers(BaseModel):
    class Meta:
        indexes = (
            (('group', 'alias'), True),
        )

    group = ForeignKeyField(Group, backref='members')
    alias = CharField()