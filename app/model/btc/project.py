"""
    :copyright: © 2021 by Alpha.
"""

from lin.interface import InfoCrud as Base
from sqlalchemy import Column, Integer, String

from app.exception.api import BtcProjectNotFound


class BtcProject(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    rang = Column(Integer)
    name = Column(String(50), nullable=False)
    english_name = Column(String(30))
    chinese_name = Column(String(30), default="未名")
    qkl_link = Column(String(255))
    website = Column(String(255))
    detail = Column(String(102400))
    info_table = Column(String(102400))
    
