import time
from datetime import datetime, timezone
from functools import wraps
from typing import Type, TypeVar, Generic, Any

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, SQLModel

from .exceptions import EntityNotFoundError, DatabaseOperationError, VersionConflictError

T = TypeVar('T', bound=SQLModel)  # 表示继承自 SQLModel 的模型类型，数据库对象
T_ID = TypeVar('T_ID', bound=Any)  # 表示主键 ID 的类型（如 int, str, UUID 等）


"""
一个全局的CRUD映射模版
注意： 
1.FastAPI DI 自动管理的 Session，可能会导致 FastAPI 的 session 生命周期异常（因为 FastAPI 管理的 session 不建议在方法内部用 with 重新包裹，会导致提前关闭，影响外层逻辑）。
如果你是结合 FastAPI 使用 Depends(get_session) 获取 session 的，CRUD 中不需要 with session，直接用。

2.FastAPI 自动生成 Swagger (OpenAPI) 的请求体 schema 依赖于 Pydantic。
而 SQLModel 是基于 Pydantic 和 SQLAlchemy 的混合，但如果泛型 T 直接绑定 SQLModel，Swagger 在解析时可能识别不了这个泛型类型，所以最终降级成 args, kwargs 这种模糊显示。
"""


class CRUDBase(Generic[T, T_ID]):  # 泛型类，支持动态绑定模型类型和主键类型
    def __init__(self, model: Type[T]):
        self.model = model  # 保存具体的模型类（如 User, Product）

    def create(self, session: Session, obj_in: T) -> T:
        try:
            # 检查输入对象类型并尝试转换
            if not isinstance(obj_in, self.model):
                try:
                    # 如果不是模型实例，尝试转换
                    obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else dict(obj_in)
                    db_obj = self.model(**obj_data)  # 尝试创建数据库对象
                except Exception as e:
                    raise ValueError(f"Input object cannot be converted to {self.model.__name__}: {str(e)}")
            else:
                db_obj = obj_in  # 如果已经是正确的类型，直接使用
            # 添加对象到会话
            session.add(db_obj)  # 将对象添加到会话
            session.commit()  # 提交事务（立即写入数据库）
            session.refresh(db_obj)  # 刷新对象以获取数据库生成的字段（如自增ID）
            return db_obj
        except SQLAlchemyError as e:
            session.rollback()  # 回滚事务
            raise DatabaseOperationError("create", str(e))

    def read(self, session: Session, entity_id: T_ID) -> T:
        """
        获取实体，如果不存在则抛出EntityNotFoundError

        Args:
            session: 数据库会话
            entity_id: 实体ID

        Returns:
            找到的实体实例

        Raises:
            EntityNotFoundError: 如果实体不存在
        """
        try:
            entity = session.get(self.model, entity_id)
            if not entity:
                raise EntityNotFoundError(self.model.__name__, entity_id)
            return entity
        except SQLAlchemyError as e:
            raise DatabaseOperationError("read", str(e))

    @staticmethod
    def retry_on_conflict(max_retries=3, delay=0.1):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                retries = 0
                while retries < max_retries:
                    try:
                        return func(*args, **kwargs)
                    except DatabaseOperationError as e:
                        if "Data has been modified" in str(e):
                            retries += 1
                            time.sleep(delay)
                        else:
                            raise
                raise DatabaseOperationError("update", "Max retries reached")
            return wrapper
        return decorator

    @retry_on_conflict(max_retries=3, delay=0.2)                        # 利用装饰器进行捕获处理乐观锁
    def update(self, session: Session, entity_id: T_ID, obj_in: T) -> T:
        entity = self.read(session, entity_id)                          # 先查询实体（确保存在）
        if entity.version != obj_in.version:                            # 检查版本号
            raise VersionConflictError(self.model.__name__, entity_id)
        data = obj_in.dict(exclude_unset=True)                          # 仅提取非默认值的字段（避免覆盖未传字段）
        for key, value in data.items():
            setattr(entity, key, value)  # 动态更新字段
        entity.version += 1  # 更新版本号
        entity.updated_at = datetime.now(timezone.utc)  # 自动更新时间，增加时区信息
        session.commit()
        session.refresh(entity)

        return entity

    def delete(self, session: Session, entity_id: T_ID) -> T:
        try:
            entity = self.read(session, entity_id)
            session.delete(entity)
            session.commit()
            return entity
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseOperationError("delete", str(e))

    def soft_delete(self, session: Session, entity_id: T_ID) -> T:
        entity = self.read(session, entity_id)
        entity.is_deleted = 1  # 已删除状态值改为整数1
        entity.deleted_at = datetime.now(timezone.utc)  # 使用带时区的时间
        session.commit()
        return entity
