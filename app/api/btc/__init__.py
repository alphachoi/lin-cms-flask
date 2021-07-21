from flask import Blueprint
from app.api.btc import project

def create_btc():
    btc_project = Blueprint('btc', __name__)
    project.project_api.register(btc_project)
    return btc_project