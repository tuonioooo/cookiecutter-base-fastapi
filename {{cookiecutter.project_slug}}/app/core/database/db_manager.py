from fastapi import Depends
from sqlalchemy import AsyncAdaptedQueuePool, URL, Select, StaticPool, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine
from typing import AsyncGenerator, Dict, Generator, Annotated, TypeVar, Type, Optional, Any, Callable, List, Union
from enum import Enum, auto
from app.core.logger import logger
from contextlib import asynccontextmanager, contextmanager
import os
import yaml
from pydantic import BaseModel, Field, model_validator, validator, root_validator
import asyncio
from functools import lru_cache
import time
from dataclasses import dataclass
from urllib.parse import quote_plus

from app.core.config import settings

# 类型变量，用于泛型函数
T = TypeVar('T', bound=SQLModel)


class DatabaseType(str, Enum):
    """数据库类型枚举"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    MSSQL = "mssql"


@dataclass
class ConnectionInfo:
    """数据库连接信息"""
    host: str
    port: int
    database: str
    username: str = ""
    password: str = ""
    
    def __post_init__(self):
        """URL编码密码中的特殊字符"""
        if self.password:
            self.password = quote_plus(self.password)


class DatabaseConfig(BaseModel):
    """数据库配置模型"""
    name: str
    db_type: DatabaseType
    sync_url: Optional[str] = None
    async_url: Optional[str] = None
    connection_info: Optional[ConnectionInfo] = None
    echo: bool = False
    pool_config: Dict[str, Any] = Field(default_factory=dict)
    connect_args: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    health_check_interval: int = Field(default=30, ge=5, le=300)  # 5-300秒范围
    max_retries: int = Field(default=3, ge=1, le=10)  # 1-10次重试
    connection_timeout: int = Field(default=30, ge=5, le=120)  # 连接超时

    @model_validator(mode="before")
    def validate_config(cls, values):
        """验证配置的完整性"""
        sync_url = values.get('sync_url')
        async_url = values.get('async_url')
        connection_info = values.get('connection_info')
        db_type = values.get('db_type')
        
        # 必须提供URL或连接信息
        if not sync_url and not connection_info:
            raise ValueError("必须提供 sync_url 或 connection_info")
        
        # 如果提供了连接信息但没有URL，自动生成URL
        if connection_info and not sync_url:
            values['sync_url'] = make_connection_url(
                db_type=db_type,
                username=connection_info.username,
                password=connection_info.password,
                host=connection_info.host,
                port=connection_info.port,
                database=connection_info.database
            )
        
        if connection_info and not async_url:
            values['async_url'] = make_async_connection_url(
                db_type=db_type,
                username=connection_info.username,
                password=connection_info.password,
                host=connection_info.host,
                port=connection_info.port,
                database=connection_info.database
            )
        
        return values
    
    def __init__(self, **data):
        super().__init__(**data)
        # SQLite特殊处理
        if self.db_type == DatabaseType.SQLITE:
            if "check_same_thread" not in self.connect_args:
                self.connect_args["check_same_thread"] = False
            # SQLite不需要连接池配置
            if not self.pool_config:
                self.pool_config = {"poolclass": StaticPool, "pool_pre_ping": True}

    @property
    def masked_sync_url(self) -> str:
        """返回掩码后的同步URL（隐藏密码）"""
        return self._mask_password_in_url(self.sync_url)
    
    @property
    def masked_async_url(self) -> str:
        """返回掩码后的异步URL（隐藏密码）"""
        return self._mask_password_in_url(self.async_url)
    
    def _mask_password_in_url(self, url: str) -> str:
        """在URL中掩码密码"""
        if not url or "://" not in url:
            return url
        
        try:
            parts = url.split("://")
            if len(parts) != 2:
                return url
            
            protocol, rest = parts
            if "@" in rest:
                auth, host_db = rest.split("@", 1)
                if ":" in auth:
                    username, _ = auth.split(":", 1)
                    return f"{protocol}://{username}:***@{host_db}"
            return url
        except Exception:
            return url


class DatabaseConfigManager:
    """数据库配置管理器"""
    def __init__(self):
        self.configs: Dict[str, DatabaseConfig] = {}
        self.default_source: str = "default"
        self._config_lock = asyncio.Lock() if hasattr(asyncio, 'current_task') else None
    
    def add_config(self, config: DatabaseConfig) -> None:
        """添加配置"""
        if config.name in self.configs:
            logger.warning(f"数据源配置已存在，将被覆盖: {config.name}")
        
        self.configs[config.name] = config
        if config.is_default:
            self.default_source = config.name
            logger.info(f"🟢 初始化数据源默认配置: {config.name} ({config.db_type}) 连接池配置{config.pool_config}")
    
    def get_config(self, name: Optional[str] = None) -> DatabaseConfig:
        """获取配置"""
        source_name = name or self.default_source
        if source_name not in self.configs:
            available = list(self.configs.keys())
            raise ValueError(f"数据源配置不存在: {source_name}, 可用配置: {available}")
        return self.configs[source_name]
    
    def remove_config(self, name: str) -> None:
        """移除配置"""
        if name == self.default_source:
            raise ValueError(f"不能移除默认数据源配置: {name}")
        if name in self.configs:
            del self.configs[name]
            logger.info(f"移除数据源配置: {name}")
    
    def load_from_yaml(self, config_path: str) -> None:
        """从YAML文件加载配置"""
        if not os.path.exists(config_path):
            logger.warning(f"配置文件不存在: {config_path}")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data or not isinstance(config_data, dict):
                logger.warning(f"配置文件格式错误: {config_path}")
                return
            
            # 处理数据库配置
            db_configs = config_data.get('databases', [])
            for db_config in db_configs:
                try:
                    config = DatabaseConfig(**db_config)
                    self.add_config(config)
                except Exception as e:
                    logger.error(f"加载数据源配置失败: {e}")
        
        except Exception as e:
            logger.error(f"加载YAML配置文件失败: {e}")
    
    def load_from_env(self) -> None:
        """从环境变量加载配置"""
        try:
            db_count = 0
            while True:
                prefix = f"DB_{db_count}_"
                name_env = f"{prefix}NAME"
                
                if name_env not in os.environ:
                    break
                
                try:
                    config_data = self._parse_env_config(prefix)
                    config = DatabaseConfig(**config_data)
                    self.add_config(config)
                except Exception as e:
                    logger.error(f"加载环境变量数据源配置失败: {e}")
                
                db_count += 1
        except Exception as e:
            logger.error(f"从环境变量加载配置失败: {e}")
    
    def _parse_env_config(self, prefix: str) -> Dict[str, Any]:
        """解析环境变量配置"""
        name = os.environ[f"{prefix}NAME"]
        db_type_str = os.environ.get(f"{prefix}TYPE", "sqlite")
        
        try:
            db_type = DatabaseType(db_type_str.lower())
        except ValueError:
            logger.warning(f"不支持的数据库类型: {db_type_str}，使用SQLite")
            db_type = DatabaseType.SQLITE
        
        config_data = {
            "name": name,
            "db_type": db_type,
            "is_default": os.environ.get(f"{prefix}DEFAULT", "false").lower() == "true",
        }
        
        # 根据数据库类型构建配置
        if db_type == DatabaseType.SQLITE:
            db_path = os.environ.get(f"{prefix}PATH", f"{name}.sqlite")
            config_data.update({
                "sync_url": f"sqlite:///{db_path}",
                "async_url": f"sqlite+aiosqlite:///{db_path}"
            })
        else:
            # 通用数据库连接参数
            connection_info = ConnectionInfo(
                username=os.environ.get(f"{prefix}USERNAME", ""),
                password=os.environ.get(f"{prefix}PASSWORD", ""),
                host=os.environ.get(f"{prefix}HOST", "localhost"),
                port=int(os.environ.get(f"{prefix}PORT", self._get_default_port(db_type))),
                database=os.environ.get(f"{prefix}DATABASE", "")
            )
            config_data["connection_info"] = connection_info
        
        # 连接池配置
        pool_config = {}
        pool_mapping = {
            "POOL_SIZE": "pool_size",
            "MAX_OVERFLOW": "max_overflow", 
            "POOL_TIMEOUT": "pool_timeout",
            "POOL_RECYCLE": "pool_recycle"
        }
        
        for env_key, pool_key in pool_mapping.items():
            env_var = f"{prefix}{env_key}"
            if env_var in os.environ:
                pool_config[pool_key] = int(os.environ[env_var])
        
        if pool_config:
            config_data["pool_config"] = pool_config
        
        # 其他配置
        optional_configs = {
            "HEALTH_CHECK_INTERVAL": "health_check_interval",
            "MAX_RETRIES": "max_retries",
            "CONNECTION_TIMEOUT": "connection_timeout"
        }
        
        for env_key, config_key in optional_configs.items():
            env_var = f"{prefix}{env_key}"
            if env_var in os.environ:
                config_data[config_key] = int(os.environ[env_var])
        
        return config_data
    
    def _get_default_port(self, db_type: DatabaseType) -> str:
        """获取数据库默认端口"""
        port_mapping = {
            DatabaseType.MYSQL: "3306",
            DatabaseType.POSTGRESQL: "5432",
            DatabaseType.ORACLE: "1521",
            DatabaseType.MSSQL: "1433"
        }
        return port_mapping.get(db_type, "5432")
    
    def load_default_config(self) -> None:
        """加载默认配置"""
        try:
            if settings.USE_SQLITE:
                sync_url = settings.SQLITE_DATABASE_URI
                async_url = settings.SQLITE_DATABASE_URI.replace("sqlite:///", "sqlite+aiosqlite:///")
                db_type = DatabaseType.SQLITE
                connect_args = {"check_same_thread": False}
                pool_config = {"poolclass": StaticPool, "pool_pre_ping": True}
            else:
                sync_url = str(settings.SQLALCHEMY_DATABASE_URI)
                async_url = str(settings.SQLALCHEMY_DATABASE_URI).replace("postgresql://", "postgresql+asyncpg://")
                db_type = DatabaseType.POSTGRESQL
                connect_args = {}
                pool_config = {
                    'pool_size': settings.POOL_SIZE,
                    'max_overflow': settings.MAX_OVERFLOW,
                    'pool_timeout': settings.POOL_TIMEOUT,
                    'pool_recycle': settings.POOL_RECYCLE,
                    'pool_pre_ping': True,  # 启用连接预检
                }
            
            config = DatabaseConfig(
                name="default",
                db_type=db_type,
                sync_url=sync_url,
                async_url=async_url,
                echo=settings.ENVIRONMENT == "local",
                pool_config=pool_config,
                connect_args=connect_args,
                is_default=True
            )
            
            self.add_config(config)
        except Exception as e:
            logger.error(f"加载默认配置失败: {e}")
            raise


class HealthChecker:
    """数据库健康检查器"""
    def __init__(self, db_manager: 'DatabaseManager'):
        self.db_manager = db_manager
        self._health_status: Dict[str, bool] = {}
        self._last_check: Dict[str, float] = {}
    
    async def check_source_health(self, source_name: str) -> bool:
        """检查单个数据源健康状态"""
        try:
            config = self.db_manager.config_manager.get_config(source_name)
            current_time = time.time()
            
            # 检查是否需要健康检查
            last_check = self._last_check.get(source_name, 0)
            if current_time - last_check < config.health_check_interval:
                return self._health_status.get(source_name, True)
            
            # 执行健康检查
            async with self.db_manager.get_async_session(source_name) as session:
                await session.execute("SELECT 1")
            
            self._health_status[source_name] = True
            self._last_check[source_name] = current_time
            return True
            
        except Exception as e:
            logger.warning(f"数据源 {source_name} 健康检查失败: {e}")
            self._health_status[source_name] = False
            self._last_check[source_name] = time.time()
            return False
    
    async def check_all_sources(self) -> Dict[str, bool]:
        """检查所有数据源健康状态"""
        tasks = []
        for source_name in self.db_manager.get_all_source_names():
            tasks.append(self.check_source_health(source_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        health_status = {}
        for i, source_name in enumerate(self.db_manager.get_all_source_names()):
            result = results[i]
            health_status[source_name] = result if isinstance(result, bool) else False
        
        return health_status


class DatabaseManager:
    """
    数据库管理器，支持多数据源管理
    
    提供同步和异步数据库连接以及会话管理，可根据不同业务需求选择不同数据源
    """
    def __init__(self, config_manager: Optional[DatabaseConfigManager] = None):
        # 存储同步引擎和会话工厂
        self._sync_engines: Dict[str, Any] = {}
        self._sync_session_factories: Dict[str, Any] = {}

        # 存储异步引擎和会话工厂
        self._async_engines: Dict[str, Any] = {}
        self._async_session_factories: Dict[str, Any] = {}

        # 配置管理器
        self.config_manager = config_manager or DatabaseConfigManager()

        # 健康检查器
        self.health_checker = HealthChecker(self)

        # 初始化标志
        self._initialized = False
        
        # 依赖缓存
        self._dependency_cache: Dict[str, Callable] = {}

        # 初始化默认数据源
        self._initialize_default_sources()
    
    def _initialize_default_sources(self):
        """初始化默认数据源"""
        try:
            # 加载默认配置
            if not self.config_manager.configs:
                self.config_manager.load_default_config()
            
            # 为所有配置创建引擎和会话
            for name, config in self.config_manager.configs.items():
                if name not in self._sync_engines:
                    self._create_engines_and_sessions(config)
            
            self._initialized = True            
            logger.info("🟢 数据库管理器初始化完成")
            
        except Exception as e:
            logger.error(f"数据库管理器初始化失败: {e}")
            raise
    
    @property 
    def default_source(self) -> str:
        """获取默认数据源名称"""
        return self.config_manager.default_source
    
    def add_source(
        self,
        name: str,
        db_type: DatabaseType,
        sync_url: Optional[str] = None,
        async_url: Optional[str] = None,
        connection_info: Optional[ConnectionInfo] = None,
        echo: Optional[bool] = None,
        pool_config: Optional[Dict[str, Any]] = None,
        connect_args: Optional[Dict[str, Any]] = None,
        is_default: bool = False,
        **kwargs
    ):
        """添加数据源"""
        if echo is None:
            echo = settings.ENVIRONMENT == "local"
        
        config = DatabaseConfig(
            name=name,
            db_type=db_type,
            sync_url=sync_url,
            async_url=async_url,
            connection_info=connection_info,
            echo=echo,
            pool_config=pool_config or {},
            connect_args=connect_args or {},
            is_default=is_default,
            **kwargs
        )
        
        self.add_source_from_config(config)
    
    def add_source_from_config(self, config: DatabaseConfig):
        """从配置对象添加数据源"""
        self.config_manager.add_config(config)
        self._create_engines_and_sessions(config) 
        
        # 清除相关的依赖缓存
        self._clear_dependency_cache(config.name)

        logger.info(f"🟢 成功添加数据源: {config.name} ({config.db_type}), 连接池配置: {config.pool_config}")

    def _create_engines_and_sessions(self, config: DatabaseConfig):
        """创建引擎和会话工厂"""
        try:
            # 创建同步引擎
            sync_engine = create_engine(
                config.sync_url,
                echo=config.echo,
                connect_args=config.connect_args,
                **config.pool_config
            )
            
            # 添加连接事件监听器
            self._setup_engine_events(sync_engine, config.name)
            
            # 创建同步会话工厂
            sync_session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=sync_engine,
                class_=Session
            )
            
            # 创建异步引擎
            async_pool_config = config.pool_config.copy()
            if 'poolclass' not in async_pool_config and config.db_type != DatabaseType.SQLITE:
                async_pool_config['poolclass'] = AsyncAdaptedQueuePool
            
            async_engine = create_async_engine(
                config.async_url,
                echo=config.echo,
                connect_args=config.connect_args,
                **async_pool_config
            )
            
            # 创建异步会话工厂
            async_session_factory = async_sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=async_engine,
                expire_on_commit=False,
                class_=AsyncSession
            )
            
            # 存储引擎和会话工厂
            self._sync_engines[config.name] = sync_engine
            self._sync_session_factories[config.name] = sync_session_factory
            self._async_engines[config.name] = async_engine
            self._async_session_factories[config.name] = async_session_factory
            logger.info(f"🟢 成功创建数据源引擎: {config.name}")
            
        except Exception as e:
            logger.error(f"创建数据源引擎失败: {config.name}, 错误: {e}")
            raise
    
    def _setup_engine_events(self, engine, source_name: str):
        """设置引擎事件监听器"""
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """SQLite特殊配置"""
            if 'sqlite' in str(engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
        
        @event.listens_for(engine, "checkout")
        def checkout_handler(dbapi_connection, connection_record, connection_proxy):
            """连接检出事件"""
            logger.debug(f"数据源 {source_name} 连接检出")
    
    async def remove_source(self, name: str):
        """移除数据源"""
        if name == self.default_source:
            logger.warning(f"不能移除默认数据源: {name}")
            return
        
        # 关闭引擎
        if name in self._sync_engines:
            try:
                self._sync_engines[name].dispose()
                logger.info(f"已关闭同步引擎: {name}")
            except Exception as e:
                logger.error(f"关闭同步引擎失败: {name}, 错误: {e}")
            finally:
                del self._sync_engines[name]
                del self._sync_session_factories[name]
        
        if name in self._async_engines:
            try:
                await self._async_engines[name].dispose()
                logger.info(f"已关闭异步引擎: {name}")
            except Exception as e:
                logger.error(f"关闭异步引擎失败: {name}, 错误: {e}")
            finally:
                del self._async_engines[name]
                del self._async_session_factories[name]
        
        # 移除配置和清除缓存
        try:
            self.config_manager.remove_config(name)
            self._clear_dependency_cache(name)
        except ValueError as e:
            logger.warning(str(e))
        
        logger.info(f"成功移除数据源: {name}")
    
    def _clear_dependency_cache(self, source_name: str):
        """清除依赖缓存"""
        keys_to_remove = [key for key in self._dependency_cache.keys() if source_name in key]
        for key in keys_to_remove:
            del self._dependency_cache[key]
    
    def get_sync_engine(self, name: Optional[str] = None):
        """获取同步引擎"""
        source_name = name or self.default_source
        if source_name not in self._sync_engines:
            available = list(self._sync_engines.keys())
            raise ValueError(f"数据源不存在: {source_name}, 可用数据源: {available}")
        return self._sync_engines[source_name]
    
    def get_async_engine(self, name: Optional[str] = None):
        """获取异步引擎"""
        source_name = name or self.default_source
        if source_name not in self._async_engines:
            available = list(self._async_engines.keys())
            raise ValueError(f"数据源不存在: {source_name}, 可用数据源: {available}")
        return self._async_engines[source_name]
    
    @contextmanager
    def get_sync_session(self, name: Optional[str] = None) -> Generator[Session, None, None]:
        """获取同步会话的上下文管理器"""
        source_name = name or self.default_source
        if source_name not in self._sync_session_factories:
            available = list(self._sync_session_factories.keys())
            raise ValueError(f"数据源不存在: {source_name}, 可用数据源: {available}")
        
        sync_session = self._sync_session_factories[source_name]
        with sync_session() as session:
            try:
                yield session
            except Exception as e:
                session.rollback()
                logger.error(f"数据源 {source_name} 会话异常: {e}")
                raise
    
    @asynccontextmanager
    async def get_async_session(self, name: Optional[str] = None):
        """获取异步会话的上下文管理器"""
        source_name = name or self.default_source
        if source_name not in self._async_session_factories:
            available = list(self._async_session_factories.keys())
            raise ValueError(f"数据源不存在: {source_name}, 可用数据源: {available}")
        
        async_session = self._async_session_factories[source_name]
        async with async_session() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"数据源 {source_name} 异步会话异常: {e}")
                raise


    # @lru_cache(maxsize=32)
    # def get_sync_session_dependency(self, name: Optional[str] = None) -> Callable:
    #     """获取同步会话的依赖函数（带缓存）"""
    #     source_name = name or self.default_source
    #     cache_key = f"sync_{source_name}"
        
    #     if cache_key not in self._dependency_cache:
    #         def _get_db():
    #             with self.get_sync_session(source_name) as session:
    #                 yield session

    #         # 包装为正确的依赖函数
    #         def _dependency():
    #             return _get_db()

    #         self._dependency_cache[cache_key] = _dependency

    #     return self._dependency_cache[cache_key]
    
    # @lru_cache(maxsize=32)
    # def get_async_session_dependency(self, name: Optional[str] = None) -> Callable:
    #     """获取异步会话的依赖函数（带缓存）"""
    #     source_name = name or self.default_source
    #     cache_key = f"async_{source_name}"
        
    #     if cache_key not in self._dependency_cache:
    #         async def _get_async_db():
    #             async with self.get_async_session(source_name) as session:
    #                 yield session

    #         # 包装为正确的依赖函数
    #         # def _dependency():
    #         #     return _get_async_db()

    #         self._dependency_cache[cache_key] = _get_async_db

    #     return self._dependency_cache[cache_key]
    
    def create_all(self, name: Optional[str] = None):
        """创建所有表"""
        source_name = name or self.default_source
        engine = self.get_sync_engine(source_name)
        SQLModel.metadata.create_all(engine)  # 仅在表不存在时创建表，不修改已有表
        logger.info(f"成功为数据源 {source_name} 创建所有表")
    
    def drop_all(self, name: Optional[str] = None):
        """删除所有表（⚠️ 谨慎使用）"""
        source_name = name or self.default_source
        engine = self.get_sync_engine(source_name)
        SQLModel.metadata.drop_all(engine)  # 删除所有表（⚠️ 会清空数据！）
        logger.warning(f"已删除数据源 {source_name} 的所有表")

    async def dispose_all(self):
        """关闭所有引擎，释放资源"""
        # 关闭同步引擎
        for name, engine in list(self._sync_engines.items()):
            try:
                engine.dispose()
                logger.info(f"已关闭同步引擎: {name}")
            except Exception as e:
                logger.error(f"关闭同步引擎失败: {name}, 错误: {e}")
        
        # 关闭异步引擎
        for name, engine in list(self._async_engines.items()):
            try:
                await engine.dispose()
                logger.info(f"已关闭异步引擎: {name}")
            except Exception as e:
                logger.error(f"关闭异步引擎失败: {name}, 错误: {e}")
        
        # 清空所有存储
        self._sync_engines.clear()
        self._sync_session_factories.clear()
        self._async_engines.clear()
        self._async_session_factories.clear()
        self._dependency_cache.clear()
        
        logger.info("所有数据库引擎已关闭")
    
    def initialize_from_yaml(self, config_path: str):
        """从YAML文件初始化数据源"""
        self.config_manager.load_from_yaml(config_path)
        
        # 为新配置创建引擎和会话
        for name, config in self.config_manager.configs.items():
            if name not in self._sync_engines:
                self._create_engines_and_sessions(config)

    def initialize_from_env(self):
        """从环境变量初始化数据源"""
        try:
            # 首先从配置管理器加载环境变量配置
            self.config_manager.load_from_env()
            
            # 为新配置创建引擎和会话
            for name, config in self.config_manager.configs.items():
                if name not in self._sync_engines:
                    self._create_engines_and_sessions(config)
                    logger.info(f"从环境变量初始化数据源: {name} ({config.db_type})")
            
            # 验证至少有一个数据源被初始化
            if not self._sync_engines:
                logger.warning("没有从环境变量中加载到任何数据源配置")
                # 如果没有环境变量配置，确保有默认配置
                if not hasattr(self, '_initialized') or not self._initialized:
                    self._initialize_default_sources()
            else:
                self._initialized = True
                logger.info(f"成功从环境变量初始化了 {len(self._sync_engines)} 个数据源")
            
        except Exception as e:
            logger.error(f"从环境变量初始化数据源失败: {e}")
            # 如果环境变量初始化失败，尝试加载默认配置作为备选
            if not self._sync_engines:
                logger.info("尝试加载默认配置作为备选")
                try:
                    self._initialize_default_sources()
                except Exception as fallback_error:
                    logger.error(f"加载默认配置也失败: {fallback_error}")
                    raise RuntimeError(f"数据源初始化完全失败: 环境变量错误={e}, 默认配置错误={fallback_error}")
            else:
                # 如果已有部分数据源，只记录警告
                logger.warning(f"部分环境变量配置加载失败，但已有 {len(self._sync_engines)} 个数据源可用")

    def get_all_source_names(self) -> List[str]:
        """获取所有数据源名称"""
        return list(self._sync_engines.keys())

    def get_source_info(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取数据源信息"""
        source_name = name or self.default_source
        config = self.config_manager.get_config(source_name)
        
        sync_engine = self.get_sync_engine(source_name)
        async_engine = self.get_async_engine(source_name)
        
        return {
            "name": source_name,
            "type": config.db_type.value,
            "sync_url": config.masked_sync_url,
            "async_url": config.masked_async_url,
            "is_default": source_name == self.default_source,
            "echo": config.echo,
            "pool_config": config.pool_config,
            "connect_args": config.connect_args,
            "health_check_interval": config.health_check_interval,
            "max_retries": config.max_retries,
            "connection_timeout": config.connection_timeout,
            "sync_engine_pool_size": getattr(sync_engine.pool, 'size', None),
            "async_engine_pool_size": getattr(async_engine.pool, 'size', None),
        }

    def get_all_sources_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有数据源信息"""
        return {
            name: self.get_source_info(name) 
            for name in self.get_all_source_names()
        }

    async def health_check(self, name: Optional[str] = None) -> Dict[str, Any]:
        """执行健康检查"""
        if name:
            # 检查单个数据源
            is_healthy = await self.health_checker.check_source_health(name)
            config = self.config_manager.get_config(name)
            return {
                "source": name,
                "healthy": is_healthy,
                "type": config.db_type.value,
                "last_check": self.health_checker._last_check.get(name, 0)
            }
        else:
            # 检查所有数据源
            health_status = await self.health_checker.check_all_sources()
            results = {}
            for source_name, is_healthy in health_status.items():
                config = self.config_manager.get_config(source_name)
                results[source_name] = {
                    "healthy": is_healthy,
                    "type": config.db_type.value,
                    "last_check": self.health_checker._last_check.get(source_name, 0)
                }
            return results

    async def reload_source_from_env(self, name: str):
        """从环境变量重新加载指定数据源"""
        try:
            # 查找环境变量配置
            db_count = 0
            target_config = None
            
            while True:
                prefix = f"DB_{db_count}_"
                name_env = f"{prefix}NAME"
                
                if name_env not in os.environ:
                    break
                
                env_name = os.environ[name_env]
                if env_name == name:
                    config_data = self.config_manager._parse_env_config(prefix)
                    target_config = DatabaseConfig(**config_data)
                    break
                
                db_count += 1
            
            if not target_config:
                raise ValueError(f"未找到数据源 {name} 的环境变量配置")
            
            # 移除旧的数据源（如果存在）
            if name in self._sync_engines:
                await self.remove_source(name)
            
            # 添加新配置
            self.add_source_from_config(target_config)
            logger.info(f"成功从环境变量重新加载数据源: {name}")
            
        except Exception as e:
            logger.error(f"从环境变量重新加载数据源失败: {name}, 错误: {e}")
            raise

    async def test_connection(self, name: Optional[str] = None, max_retries: Optional[int] = None) -> Dict[str, Any]:
        """测试数据库连接"""
        source_name = name or self.default_source
        config = self.config_manager.get_config(source_name)
        retries = max_retries or config.max_retries
        
        result = {
            "source": source_name,
            "sync_connection": False,
            "async_connection": False,
            "errors": []
        }
        
        # 测试同步连接
        for attempt in range(retries):
            try:
                with self.get_sync_session(source_name) as session:
                    session.execute("SELECT 1")
                result["sync_connection"] = True
                break
            except Exception as e:
                error_msg = f"同步连接尝试 {attempt + 1}/{retries} 失败: {e}"
                result["errors"].append(error_msg)
                if attempt < retries - 1:
                    await asyncio.sleep(1)  # 重试间隔
        
        # 测试异步连接
        for attempt in range(retries):
            try:
                async with self.get_async_session(source_name) as session:
                    await session.execute("SELECT 1")
                result["async_connection"] = True
                break
            except Exception as e:
                error_msg = f"异步连接尝试 {attempt + 1}/{retries} 失败: {e}"
                result["errors"].append(error_msg)
                if attempt < retries - 1:
                    await asyncio.sleep(1)  # 重试间隔
        
        result["success"] = result["sync_connection"] and result["async_connection"]
        return result
    

# 辅助函数：创建数据库连接URL
def make_connection_url(
    db_type: DatabaseType,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str,
    driver: str = None,
    **kwargs
) -> str:
    """
    创建数据库连接URL
    
    Args:
        db_type: 数据库类型
        username: 用户名
        password: 密码
        host: 主机地址
        port: 端口
        database: 数据库名
        driver: 驱动程序
        **kwargs: 额外参数
    
    Returns:
        str: 数据库连接URL
    """
    # 根据不同数据库类型构建URL
    if db_type == DatabaseType.MYSQL:
        driver = driver or "pymysql"
        return f"mysql+{driver}://{username}:{password}@{host}:{port}/{database}"
    
    elif db_type == DatabaseType.POSTGRESQL:
        driver = driver or "psycopg2"
        return f"postgresql+{driver}://{username}:{password}@{host}:{port}/{database}"
    
    elif db_type == DatabaseType.SQLITE:
        return f"sqlite:///{database}"
    
    elif db_type == DatabaseType.ORACLE:
        driver = driver or "cx_oracle"
        return f"oracle+{driver}://{username}:{password}@{host}:{port}/{database}"
    
    elif db_type == DatabaseType.MSSQL:
        driver = driver or "pyodbc"
        return f"mssql+{driver}://{username}:{password}@{host}:{port}/{database}"
    
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


# 构建异步数据库连接URL
def make_async_connection_url(
    db_type: DatabaseType,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str,
    **kwargs
) -> str:
    """
    创建异步数据库连接URL
    
    Args:
        db_type: 数据库类型
        username: 用户名
        password: 密码
        host: 主机地址
        port: 端口
        database: 数据库名
        **kwargs: 额外参数
    
    Returns:
        str: 异步数据库连接URL
    """
    # 根据不同数据库类型构建异步URL
    if db_type == DatabaseType.MYSQL:
        return f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database}"
    
    elif db_type == DatabaseType.POSTGRESQL:
        return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
    
    elif db_type == DatabaseType.SQLITE:
        return f"sqlite+aiosqlite:///{database}"
    
    # 其他数据库类型可能需要特定的异步驱动
    else:
        raise ValueError(f"不支持的异步数据库类型: {db_type}")
    
    

# 创建全局数据库管理器实例
config_manager = DatabaseConfigManager()
db_manager = DatabaseManager(config_manager)


# 导出默认依赖项 - 使用延迟获取避免初始化顺序问题
def get_db_session():
    """获取默认数据库会话依赖"""
    with db_manager.get_sync_session() as session:
        yield session

async def get_async_db_session():
    """获取默认异步数据库会话依赖"""
    async with db_manager.get_async_session() as session:
        yield session

# 导出Annotated依赖类型
DbSessionDep = Annotated[Session, Depends(get_db_session)]
AsyncDbSessionDep = Annotated[AsyncSession, Depends(get_async_db_session)]

# 导出常用的数据库管理器方法，方便使用
def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager

def get_session(source_name: Optional[str] = None):
    """获取指定数据源的同步会话上下文管理器"""
    return db_manager.get_sync_session(source_name)

async def get_async_session(source_name: Optional[str] = None):
    """获取指定数据源的异步会话上下文管理器"""
    return await db_manager.get_async_session(source_name)


# 添加清理函数，用于应用关闭时调用
async def cleanup_database_connections():
    """清理所有数据库连接"""
    try:
        await db_manager.dispose_all()
        logger.info("数据库连接清理完成")
    except Exception as e:
        logger.error(f"数据库连接清理失败: {e}")




# 使用示例 参考 `tests/database-manager-example.py`

