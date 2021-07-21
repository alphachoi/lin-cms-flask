from lin.redprint import Redprint
from lin.exception import NotFound, Success
from lin.apidoc import api
from app.model.v1.book import Book
from app.validator.book import BookQuerySearchSchema, BookSchema
from flask import g, request


book_api = Redprint('e')


@book_api.route('/<int:id>')
def get_book(id):
    # 通过Book模型在数据库中查询id=`id`, 且没有被软删除的书籍
    book = Book.query.filter_by(id=id, delete_time=None).first()
    if book:
        return book # 如果存在，返回该数据的信息
    raise NotFound('没有找到相关书籍') # 如果书籍不存在，返回一个异常给前端
 



@book_api.route('/search', methods=['GET'])
# 使用校验，需要引入定义好的对象`api`,它是Spectree的一个实例
# query代表来自url中的参数，如`http://127.0.0.1:5000?q=abc&page=1`中的 `q` 和 `page`都属于query参数
@api.validate(query=BookQuerySearchSchema)
def search_book():
    # 使用这种方式校验通过的参数将会被挂载到g的对应属性上，方便直接取用。
    q = '%' + g.q + '%' # 取出参数中的`q`参数，加`%`进行模糊查询
    books = Book.query.filter(Book.title.like(q), Book.delete_time==None).all() # 搜索书籍标题
    if books:
        return books
    raise NotFound('没有找到相关书籍')

@book_api.route("", methods=["POST"])
# json代表来自请求体body中的参数
@api.validate(json=BookSchema)
def create_book():
    # 请求体的json 数据位于 request.context.json
    book_schema = request.context.json
    Book.create(**book_schema.dict(), commit=True)
    # 12 是 消息码
    return Success(12)

@book_api.route("/<int:id>", methods=["PUT"])
@api.validate(json=BookSchema)
def update_book(id: int):
    book_schema = request.context.json
    book = Book.get(id=id)
    if book:
        book.update(
            id=id,
            **book_schema.dict(),
            commit=True,
        )
        return Success(13)
    raise NotFound(10020)

@book_api.route("/<int:id>", methods=["DELETE"])
def delete_book(id: int):
    """
    传入id删除对应图书
    """
    book = Book.get(id=id)
    if book:
        # 删除图书，软删除
        book.delete(commit=True)
        return Success(14)
    raise NotFound(10020)

@book_api.route("")
def get_books():
    """
    获取图书列表
    """
    return Book.get(one=False)