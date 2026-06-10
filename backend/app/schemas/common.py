from apiflask.fields import String, Integer
from apiflask.schemas import Schema


class PaginationQuery(Schema):
    page = Integer(load_default=1)
    per_page = Integer(load_default=20)


class MessageOut(Schema):
    message = String()
