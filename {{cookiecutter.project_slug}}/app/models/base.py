from datetime import datetime, timezone
import secrets
from typing import TypeVar, Generic, Optional, Protocol, Any
from uuid import UUID, uuid4

from pydantic import field_serializer, Field as PydanticField
from sqlmodel import Field, SQLModel, Index, Text, Column, DateTime, func, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import event


T_ID = TypeVar("T_ID", int, str, UUID)  # 泛型 ID，可以是 int 或 str，后续可以扩展 UUID

"""
SQLModel 不支持泛型, Generic[T_ID]，会报错：TypeError: issubclass() arg 1 must be a class
⚙️ 说明：
* Optional[T_ID] 表示 ID 可为空（适用于新增时自动生成）。
* server_default=func.now() 实现自动填充创建时间
* onupdate=func.now() 实现自动填充更新时间。
* is_deleted 实现逻辑删除（软删除）。
* version 用于乐观锁。


# before
Base = declarative_base()

# now

from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):

    pass
"""


from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    """替换 declarative_base() 的基类"""
    pass


# 生成无横杠 UUID 的函数
def uuid4_hex() -> str:
    """
    生成无横杠的UUID字符串
    :return: 32位无横杠UUID字符串
    """
    return str(uuid4()).replace("-", "")


class IntIDMixin(SQLModel):
    """
    整型自增主键 ID Mixin
    """
    id: int = Field(nullable=False, primary_key=True)


class UUIDIDMixin(SQLModel):
    """
    UUID主键 ID Mixin
    默认工厂采用uuid4自动创建
    """
    id: UUID = Field(nullable=False, primary_key=True, default_factory=uuid4, index=True)


class UUIDIDHexMixin(SQLModel):
    """
    字符串UUID主键 ID Mixin
    默认工厂采用uuid4_hex方法自动创建无横杠 UUID
    """
    id: str = Field(nullable=False, primary_key=True, default_factory=uuid4_hex, index=True)


class StrMixin(SQLModel):
    """
    字符串主键 ID Mixin
    """
    id: str = Field(nullable=False, primary_key=True)


class BaseSqlModel(SQLModel):
    version: int = Field(default=0, nullable=False, description="乐观锁版本号")
    created_at: datetime = Field(default_factory=datetime.now, nullable=False, description="创建时间")
    """
    采用 sa_type、sa_column_kwargs完全自定义列的方式 来避免如下错误：
    SQLModelArgumentError: Column object 'xx' already assigned to Table 'xx'
    https://github.com/fastapi/sqlmodel/discussions/743
    """
    updated_at: Optional[datetime] = Field(
        sa_type=DateTime(timezone=True), 
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
            "nullable": False,
            "comment": "更新时间"
        },
    )
    
    is_deleted: int = Field(
        sa_type=Integer,
        sa_column_kwargs={
            "default": False,
            "nullable": False,
            "comment": "逻辑删除标志"
        },
    )
    
    deleted_at: Optional[datetime] = Field(
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "nullable": True,
            "comment": "删除时间"
        },
    )
    """
    基础SQL模型
    现在只继承共享字段，但自身不定义新字段，避免重复
    """
    # @field_serializer('created_at', 'updated_at', 'deleted_at', when_used='json')
    # def serialize_datetime(self, value: datetime | None):
    #     """
    #     自动序列化时间为ISO格式，包含时区信息
    #     :param value: 日期时间对象
    #     :return: 格式化的日期时间字符串
    #     """
    #     if value is None:
    #         return None
    #     return value.astimezone(timezone.utc).isoformat()
    
    @field_serializer('created_at', 'updated_at', 'deleted_at', when_used='json')
    def serialize_datetime(self, value: datetime):
        """
        自动序列化时间
        :param value:
        :return:
        """
        if value is None:
            return None
        return value.strftime('%Y/%m/%d %H:%M:%S')
    
    def soft_delete(self) -> None:
        """
        软删除方法
        设置删除标志为True并记录删除时间
        """
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
    
    # 当从数据库查询返回 ORM 对象时，Pydantic 会通过属性访问获取数据
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "version": 0,
                "created_at": "2023-01-01T00:00:00+00:00",
                "updated_at": "2023-01-01T00:00:00+00:00",
                "is_deleted": False,
                "deleted_at": None
            }
        }
    }


class BaseSqlModelWithOperator(BaseSqlModel):
    """
    带操作者信息的基础SQL模型
    扩展了基础模型，增加了创建者和更新者字段
    """
    created_by: Optional[str] = Field(
        default=None, 
        max_length=36,
        description="创建者ID"
    )
    updated_by: Optional[str] = Field(
        default=None, 
        max_length=36,
        description="更新者ID"
    )
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "created_by": "user_id_123",
                "updated_by": "user_id_456"
            }
        }
    }

# 设置事件监听器，自动增加版本号
@event.listens_for(BaseSqlModel, 'before_update', propagate=True)
def increment_version(mapper, connection, target):
    """
    在更新前自动增加版本号
    """
    target.version += 1

