"""
        :copyright: © 2020 by the Lin team.
        :license: MIT, see LICENSE for more details.
    """

from app import create_app
from app.config.code_message import MESSAGE
from app.config.http_status_desc import DESC
from app.model.lin import (
    Group,
    GroupPermission,
    Permission,
    User,
    UserGroup,
    UserIdentity,
)

app = create_app(
    group_model=Group,
    user_model=User,
    group_permission_model=GroupPermission,
    permission_model=Permission,
    identity_model=UserIdentity,
    user_group_model=UserGroup,
    config_MESSAGE=MESSAGE,
    config_DESC=DESC,
)


if app.config.get("ENV") != "production":

    @app.route('/')
    def root():
        return app.send_static_file('logo.png')


if __name__ == "__main__":
    app.logger.warning(
        """
        ----------------------------
        |  app.run() => flask run  |
        ----------------------------
        """
    )
    app.run()
