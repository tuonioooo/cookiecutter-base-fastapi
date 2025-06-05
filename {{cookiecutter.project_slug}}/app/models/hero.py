from pydantic import BaseModel
from sqlmodel import Field, String, Integer
from app.models.base import BaseSqlModel, IntIDMixin


class Hero(BaseSqlModel, IntIDMixin, table=True):
    """英雄模型类"""
    __tablename__ = "hero"
    __table_args__ = {'comment': '英雄信息表'}
    name: str = Field(
        sa_type=String(100),
        sa_column_kwargs={
            "index": True,
            "nullable": False,
            "comment": "英雄名称"
        },
    )
    age: int | None = Field(
        sa_type=Integer,
        sa_column_kwargs={
            "index": True,
            "nullable": True,
            "comment": "年龄"
        },
    )
    secret_name: str = Field(
        sa_type=String(100),
        sa_column_kwargs={
            "nullable": False,
            "comment": "秘密身份"
        },
    )

    model_config = {
        "from_attributes": True
    }


class HeroQo(BaseModel):
    """英雄查询对象"""
    name: str | None = Field(
        default=None,
        description="英雄名称"
    )
    age: int | None = Field(
        default=None,
        ge=0,
        le=1000,
        description="年龄"
    )
    secret_name: str | None = Field(
        default=None,
        description="秘密身份"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "name": "Spider-Man",
                "age": 25,
                "secret_name": "Peter Parker"
            }
        }
    }
