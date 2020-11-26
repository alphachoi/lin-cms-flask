"""
     core module of Lin.
     ~~~~~~~~~

     manager and main db models.

    :copyright: © 2020 by the Lin team.
    :license: MIT, see LICENSE for more details.
"""
import json
from collections import namedtuple
from datetime import date, datetime

from flask import Blueprint
from flask import Flask as _Flask
from flask import current_app, g, jsonify, request
from flask.json import JSONEncoder as _JSONEncoder
from flask.wrappers import Response
from werkzeug.exceptions import HTTPException
from werkzeug.local import LocalProxy

from .config import Config
from .db import MixinJSONSerializer, db
from .exception import (APIException, InternalServerError, NotFound,
                        ParameterError, UnAuthentication)
from .interface import UserInterface, LinModel
from .jwt import jwt
from .logger import LinLog


class Flask(_Flask):

    def make_lin_response(self, rv):
        """
        将视图函数返回的值转换为flask内置支持的类型
        """
        if isinstance(rv, (MixinJSONSerializer, LinModel)):
            rv = jsonify(rv)
        elif isinstance(rv, (int, list, set)):
            rv = json.dumps(rv, cls=JSONEncoder)
        elif isinstance(rv, (tuple)):
            if len(rv) == 0 or len(rv) > 0 and not isinstance(rv[0], Response):
                rv = json.dumps(rv, cls=JSONEncoder)
        return super(Flask, self).make_response(rv)


__version__ = '0.1.3'

# 路由函数的权限和模块信息(meta信息)
Meta = namedtuple('meta', ['auth', 'module', 'mount'])

#       -> endpoint -> func
# auth                      -> module
#       -> endpoint -> func

# 记录路由函数的权限和模块信息
permission_meta_infos = {}

# config for Lin plugins
# we always access config by flask, but it dependents on the flask context
# so we move the plugin config here,which you can access config more convenience

lin_config = Config()


def permission_meta(auth, module='common', mount=True):
    """
    记录路由函数的信息
    记录路由函数访问的推送信息模板
    注：只有使用了 permission_meta 装饰器的函数才会被记录到权限管理的map中
    :param auth: 权限
    :param module: 所属模块
    :param mount: 是否挂在到权限中（一些视图函数需要说明，或暂时决定不挂在到权限中，则设置为False）
    :return:
    """

    def wrapper(func):
        name = func.__name__ + str(func.__hash__())
        existed = permission_meta_infos.get(
            name, None) and permission_meta_infos.get(name).module == module
        if existed:
            raise Exception(
                "func's name cant't be repeat in a same module")
        else:
            permission_meta_infos.setdefault(name, Meta(auth, module, mount))
        return func

    return wrapper


def find_user(**kwargs):
    return manager.find_user(**kwargs)


def find_group(**kwargs):
    return manager.find_group(**kwargs)


def find_group_ids_by_user_id(user_id):
    return manager.group_model.select_ids_by_user_id(user_id)


def get_ep_infos():
    """ 返回权限管理中的所有视图函数的信息，包含它所属module """
    info_list = manager.permission_model.query.filter_by(mount=True).all()
    infos = {}
    for permission in info_list:
        module = infos.get(permission.module, None)
        if module:
            module.append(permission)
        else:
            infos.setdefault(permission.module, [permission])

    return infos


def find_info_by_ep(ep):
    """ 通过请求的endpoint寻找路由函数的meta信息"""
    info = manager.ep_meta.get(ep)
    return info if info.mount else None


def is_user_allowed(group_ids):
    """查看当前user有无权限访问该路由函数"""
    ep = request.endpoint
    # 根据 endpoint 查找 authority, 一定存在
    meta = manager.ep_meta.get(ep)
    # 判断 用户组拥有的权限是否包含endpoint标记的权限
    return manager.permission_model.exist_by_group_ids_and_module_and_name(
        group_ids, meta.module, meta.auth)


def find_auth_module(auth):
    """ 通过权限寻找meta信息"""
    for _, meta in manager.ep_meta.items():
        if meta.auth == auth:
            return meta
    return None


class Lin(object):

    def __init__(self,
                 app: Flask = None,  # flask app , default None
                 group_model=None,  # group model, default None
                 user_model=None,  # user model, default None
                 permission_model=None,  # permission model, default None
                 group_permission_model=None,  # group permission 多对多关联模型
                 user_group_model=None,  # user group 多对多关联模型
                 create_all=True,  # 是否创建所有数据库表, default false
                 mount=True,  # 是否挂载默认的蓝图, default True
                 handle=True,  # 是否使用全局异常处理, default True
                 json_encoder=True,  # 是否使用自定义的json_encoder , default True
                 lin_response=True,  # 是否启用自动序列化，default True, 需要启用json_encoder才能生效
                 logger=True,   # 是否使用自定义系统日志，default True
                 ):
        self.app = app
        self.manager = None
        if app is not None:
            self.init_app(app,
                          group_model,
                          user_model,
                          permission_model,
                          group_permission_model,
                          user_group_model,
                          create_all,
                          mount,
                          handle,
                          json_encoder,
                          lin_response,
                          logger)

    def init_app(self,
                 app: Flask,
                 group_model=None,
                 user_model=None,
                 permission_model=None,
                 group_permission_model=None,
                 user_group_model=None,
                 create_all=False,
                 mount=True,
                 handle=True,
                 json_encoder=True,
                 lin_response=True,
                 logger=True
                 ):
        # default config
        app.config.setdefault('PLUGIN_PATH', {})
        # 默认蓝图的前缀
        app.config.setdefault('BP_URL_PREFIX', '/plugin')
        # 默认文件上传配置
        app.config.setdefault('FILE', {
            "STORE_DIR": 'app/assets',
            "SINGLE_LIMIT": 1024 * 1024 * 2,
            "TOTAL_LIMIT": 1024 * 1024 * 20,
            "NUMS": 10,
            "INCLUDE": set(['jpg', 'png', 'jpeg']),
            "EXCLUDE": set([])
        })
        json_encoder and self._enable_json_encoder(app)
        json_encoder and lin_response and self._enable_lin_response(app)
        self.app = app
        # 初始化 manager
        self.manager = Manager(app.config.get('PLUGIN_PATH'),
                               group_model,
                               user_model,
                               permission_model,
                               group_permission_model,
                               user_group_model
                               )
        self.app.extensions['manager'] = self.manager
        db.init_app(app)
        create_all and self._enable_create_all(app)
        jwt.init_app(app)
        mount and self.mount(app)
        handle and self.handle_error(app)
        logger and LinLog(app)
        self.init_permissions(app)

    def init_permissions(self, app):
        with app.app_context():
            permissions = manager.permission_model.get(one=False)
            # 新增的权限记录
            new_added_permissions = list()
            deleted_ids = [permission.id for permission in permissions]
            # mount-> unmount 的记录
            unmounted_ids = list()
            # unmount-> mount 的记录
            mounted_ids = list()
            # 用代码中记录的权限比对数据库中的权限
            for ep, meta in self.manager.ep_meta.items():
                name, module, mount = meta
                # db_existed 判定 代码中的权限是否存在于权限表记录中
                db_existed = False
                for permission in permissions:
                    if permission.name == name and permission.module == module:
                        # 此条记录存在，不会被删除
                        deleted_ids.remove(permission.id)
                        # 此条记录存在，不需要添加到权限表
                        db_existed = True
                        # 判定mount的变动情况，将记录id添加到对应的列表中
                        if permission.mount != mount:
                            if mount:
                                mounted_ids.append(permission.id)
                            else:
                                unmounted_ids.append(permission.id)
                        break
                # 遍历结束，代码中的记录不存在于已有的权限表中，则将其添加到新增权限记录列表
                if not db_existed:
                    permission = self.manager.permission_model()
                    permission.name = name
                    permission.module = module
                    permission.mount = mount
                    new_added_permissions.append(permission)
            with db.auto_commit():
                if new_added_permissions:
                    db.session.add_all(new_added_permissions)
                if unmounted_ids:
                    manager.permission_model.query.filter(
                        manager.permission_model.id.in_(unmounted_ids)).update({"mount": False}, synchronize_session=False)
                if mounted_ids:
                    manager.permission_model.query.filter(
                        manager.permission_model.id.in_(mounted_ids)).update({"mount": True}, synchronize_session=False)
                if deleted_ids:
                    manager.permission_model.query.filter(manager.permission_model.id.in_(
                        deleted_ids)).delete(synchronize_session=False)
                    # 分组-权限关联表中的数据也要清理
                    manager.group_permission_model.query.filter(manager.group_permission_model.permission_id.in_(
                        deleted_ids)).delete(synchronize_session=False)

    def mount(self, app):
        # 加载默认插件路由
        bp = Blueprint('plugin', __name__)
        # 加载插件的路由
        for plugin in self.manager.plugins.values():
            if len(plugin.controllers.values()) > 1:
                for controller in plugin.controllers.values():
                    controller.register(bp, url_prefix='/' + plugin.name)
            else:
                for controller in plugin.controllers.values():
                    controller.register(bp)
        app.register_blueprint(bp, url_prefix=app.config.get('BP_URL_PREFIX'))
        for ep, func in app.view_functions.items():
            info = permission_meta_infos.get(
                func.__name__ + str(func.__hash__()), None)
            if info:
                self.manager.ep_meta.setdefault(ep, info)

    def handle_error(self, app):
        @app.errorhandler(Exception)
        def handler(e):
            if isinstance(e, APIException):
                return e
            if isinstance(e, HTTPException):
                code = e.code
                message = e.description
                message_code = 20000
                return APIException(message_code, message).set_code(code)
            else:
                if not app.config['DEBUG']:
                    import traceback
                    app.logger.error(traceback.format_exc())
                    return InternalServerError()
                else:
                    raise e

    def _enable_json_encoder(self, app):
        app.json_encoder = JSONEncoder

    def _enable_lin_response(self, app):
        app.make_response = app.make_lin_response

    def _enable_create_all(self, app):
        with app.app_context():
            db.create_all()


class Manager(object):
    """ manager for lin """

    # 路由函数的meta信息的容器
    ep_meta = {}

    def __init__(self,
                 plugin_path,
                 group_model=None,
                 user_model=None,
                 permission_model=None,
                 group_permission_model=None,
                 user_group_model=None
                 ):
        if not group_model:
            from .model.group import Group
            self.group_model = Group
        else:
            self.group_model = group_model

        if not user_model:
            self.user_model = User
        else:
            self.user_model = user_model

        if not permission_model:
            from .model.permission import Permission
            self.permission_model = Permission
        else:
            self.permission_model = permission_model

        if not group_permission_model:
            from .model.group_permission import GroupPermission
            self.group_permission_model = GroupPermission
        else:
            self.group_permission_model = group_permission_model

        if not user_group_model:
            from .model.user_group import UserGroup
            self.user_group_model = UserGroup
        else:
            self.user_group_model = user_group_model

        from .loader import Loader
        self.loader: Loader = Loader(plugin_path)

    def find_user(self, **kwargs):
        return self.user_model.query.filter_by(**kwargs).first()

    def verify_user(self, username, password):
        return self.user_model.verify(username, password)

    def find_group(self, **kwargs):
        return self.group_model.query.filter_by(**kwargs).first()

    @property
    def plugins(self):
        return self.loader.plugins

    def get_plugin(self, name):
        return self.loader.plugins.get(name)

    def get_model(self, name):
        # attention!!! if models have the same name,will return the first one
        # 注意！！！ 如果容器内有相同的model，则默认返回第一个
        for plugin in self.plugins.values():
            return plugin.models.get(name)

    def get_service(self, name):
        # attention!!! if services have the same name,will return the first one
        # 注意！！！ 如果容器内有相同的service，则默认返回第一个
        for plugin in self.plugins.values():
            return plugin.services.get(name)


# a proxy for manager instance
# attention, only used when context in  stack

# 获得manager实例
# 注意，仅仅在flask的上下文栈中才可获得
manager: Manager = LocalProxy(lambda: get_manager())


def get_manager():
    _manager = current_app.extensions['manager']
    if _manager:
        return _manager
    else:
        app = current_app._get_current_object()
        with app.app_context():
            return app.extensions['manager']


class User(UserInterface, db.Model):

    @classmethod
    def verify(cls, username, password):
        user = cls.query.filter_by(username=username).first()
        if user is None or user.delete_time is not None:
            raise NotFound('用户不存在')
        if not user.check_password(password):
            raise ParameterError('密码错误，请输入正确密码')
        if not user.is_active:
            raise UnAuthentication('您目前处于未激活状态，请联系超级管理员')
        return user

    def reset_password(self, new_password):
        #: attention,remember to commit
        #: 注意，修改密码后记得提交至数据库
        self.password = new_password

    def change_password(self, old_password, new_password):
        #: attention,remember to commit
        #: 注意，修改密码后记得提交至数据库
        if self.check_password(old_password):
            self.password = new_password
            return True
        return False

    @classmethod
    def select_page_by_group_id(cls, group_id, root_group_id) -> list:
        '''
        通过分组id分页获取用户数据
        '''
        query = db.session.query(manager.user_group_model.user_id).filter(
            manager.user_group_model.group_id == group_id,
            manager.user_group_model.group_id != root_group_id)
        result = cls.query.filter_by(soft=True).filter(cls.id.in_(query))
        users = result.all()
        return users


class JSONEncoder(_JSONEncoder):
    def default(self, o):
        if hasattr(o, 'keys') and hasattr(o, '__getitem__'):
            return dict(o)
        if isinstance(o, datetime):
            return o.strftime('%Y-%m-%dT%H:%M:%SZ')
        if isinstance(o, date):
            return o.strftime('%Y-%m-%d')
        return JSONEncoder.default(self, o)
