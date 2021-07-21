"""
    :copyright: © 2020 by the Lin team.
    :license: MIT, see LICENSE for more details.
"""

from lin.apidoc import BaseModel


class BtcProjectQuerySearchSchema(BaseModel):
    q: str

class BtcProjectSchema(BaseModel):
    name: str
    english_name: str
    chinese_name: str
    detail: str