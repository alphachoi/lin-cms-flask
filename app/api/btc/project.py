from lin.redprint import Redprint
from lin.exception import NotFound, Success
from lin.apidoc import api
from app.model.btc import project
from app.model.btc.project import BtcProject
from app.validator.project import BtcProjectQuerySearchSchema, BtcProjectSchema
from flask import g, request


project_api = Redprint('project')


@project_api.route('/<int:id>')
def get_project(id):
    # 在数据库中查询id=`id`, 且没有被软删除的项目
    project = BtcProject.query.filter_by(id=id, delete_time=None).first()
    if project:
        return project # 如果存在，返回该数据的信息
    raise NotFound('没有找到相关项目') 

@project_api.route('/search', methods=['GET'])
# 使用校验，需要引入定义好的对象`api`,它是Spectree的一个实例
# query代表来自url中的参数，如`http://127.0.0.1:5000?q=abc&page=1`中的 `q` 和 `page`都属于query参数
@api.validate(query=BtcProjectQuerySearchSchema)
def search_project():
    # 使用这种方式校验通过的参数将会被挂载到g的对应属性上，方便直接取用。
    q = '%' + g.q + '%' # 取出参数中的`q`参数，加`%`进行模糊查询
    projects = BtcProject.query.filter(BtcProject.name.like(q), BtcProject.delete_time==None).all() # 搜索书籍标题
    if projects:
        return projects
    raise NotFound('没有找到相关项目')

@project_api.route("", methods=["POST"])
# json代表来自请求体body中的参数
@api.validate(json=BtcProjectSchema)
def create_project():
    # 请求体的json 数据位于 request.context.json
    project_schema = request.context.json
    BtcProject.create(**project_schema.dict(), commit=True)
    # 12 是 消息码
    return Success(12)

@project_api.route("/<int:id>", methods=["PUT"])
@api.validate(json=BtcProjectSchema)
def update_project(id: int):
    project_schema = request.context.json
    project = BtcProject.get(id=id)
    if project:
        project.update(
            id=id,
            **project_schema.dict(),
            commit=True,
        )
        return Success(13)
    raise NotFound(10020)

@project_api.route("/<int:id>", methods=["DELETE"])
def delete_project(id: int):
    """
    传入id删除对应项目
    """
    project = BtcProject.get(id=id)
    if project:
        # 删除图书，软删除
        project.delete(commit=True)
        return Success(14)
    raise NotFound(10020)

@project_api.route("")
def get_projects():
    """
    获取项目列表
    """
    return BtcProject.get(one=False)