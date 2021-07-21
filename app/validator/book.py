"""
    :copyright: © 2020 by the Lin team.
    :license: MIT, see LICENSE for more details.
"""

from lin.apidoc import BaseModel


class BookQuerySearchSchema(BaseModel):
    q: str

class BookSchema(BaseModel):
    title: str
    author: str
    image: str
    summary: str