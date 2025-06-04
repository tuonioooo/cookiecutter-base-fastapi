from contextlib import asynccontextmanager
from fastapi import Depends
from app.core.config import settings
from app.core.database.db_manager import db_manager, DatabaseConfig, DatabaseType, ConnectionInfo
from app.core.logger import logger
from sqlmodel import Session, SQLModel, create_engine
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

#==============================Mysql数据库配置==============================


DB_MYSQL_NAME = "mysql"

# 添加额外数据源的逻辑优化
def _setup_additional_datasources():
    """设置额外的数据源"""
    try:
        # 如果配置了MySQL，添加MySQL数据源
        if all([settings.MYSQL_USER, settings.MYSQL_PASSWORD, settings.MYSQL_DB]):
            mysql_config = DatabaseConfig(
                name=DB_MYSQL_NAME,
                db_type=DatabaseType.MYSQL,
                connection_info=ConnectionInfo(
                    host=settings.MYSQL_SERVER,
                    port=settings.MYSQL_PORT,
                    database=settings.MYSQL_DB,
                    username=settings.MYSQL_USER,
                    password=settings.MYSQL_PASSWORD
                ),
                pool_config={
                    'pool_size': settings.POOL_SIZE,
                    'max_overflow': settings.MAX_OVERFLOW,
                    'pool_timeout': settings.POOL_TIMEOUT,
                    'pool_recycle': settings.POOL_RECYCLE,
                    'pool_pre_ping': True,  # 添加连接预检
                },
                is_default=False,  # 明确设置为非默认
                echo=settings.ENVIRONMENT == "local"  # 根据环境决定是否打印SQL
            )

            db_manager.add_source_from_config(mysql_config)
            logger.info("🟢 成功添加MySQL数据源")
        else:
            logger.info("MySQL配置不完整，跳过MySQL数据源添加")
            
        # 可以继续添加其他数据源
        # if settings.REDIS_URL:
        #     # 添加Redis等其他数据源
        #     pass
            
    except Exception as e:
        logger.error(f"设置额外数据源失败: {e}")
        # 不抛出异常，让系统继续使用默认数据源

# 执行额外数据源设置
_setup_additional_datasources()

def get_mysql_db():
    """MySQL数据库会话依赖"""
    with db_manager.get_sync_session(DB_MYSQL_NAME) as session:
        yield session


# 方法一
# @asynccontextmanager 加不加都可以
async def get_mysql_async_db():
    """MySQL异步数据库会话依赖"""
    async with db_manager.get_async_session(DB_MYSQL_NAME) as session:
        yield session

# 方法二
# async def get_async_db_session():
#     async with AsyncSession(db_manager.get_async_engine(DB_MYSQL_NAME)) as session:
#         yield session

# 导出Annotated依赖类型
toolMysqlAsyncDbSessionDep = Annotated[AsyncSession, Depends(get_mysql_async_db)]
toolMysqlDbSessionDep = Annotated[Session, Depends(get_mysql_db)]