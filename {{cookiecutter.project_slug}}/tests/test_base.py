import logging
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlmodel import Session
from sqlalchemy.orm import sessionmaker

from app.core.database.db_manager import get_db_session
from app.app_factory import create_app
from app.core.config import settings

"""
pytest 教程
https://www.yuque.com/tuonioooo/cyaz9e/lldrgmlq3gvx2zwr

说明:

from sqlmodel import Session
class_= Session 避免错误 ：AttributeError: 'Session' object has no attribute 'exec'
SessionLocal = sessionmaker(autocommit=False, 
                            autoflush=False, bind=engine,
                            class_=Session
                            ) 
 @see: https://github.com/fastapi/sqlmodel/issues/75


"""

class TestBase:
    """测试基类"""
    
    # 使用类变量存储数据库配置
    SQLALCHEMY_DATABASE_URL = "sqlite:///./tests/test.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, 
                            autoflush=False, bind=engine,
                            class_=Session
                            ) 

    @classmethod
    def get_db(cls):
        """获取数据库会话"""
        db = cls.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @pytest.fixture
    def client(self, headers):
        """FastAPI测试客户端"""
        app = create_app()
        # 覆盖默认的数据库session
        app.dependency_overrides[get_db_session] = self.get_db
        with TestClient(app, headers=headers) as client:
            yield client

    @pytest.fixture(scope="module", autouse=True)
    def headers(self):
        """FastAPI模拟header"""
        return {
            "X-API-KEY": "test-api-key",
            "X-AUTH-API-KEY": "test-auth-key",
            "Content-Type": "application/json"
        }

    @pytest.fixture(scope="session", autouse=True)
    def override_settings(self):
        """覆盖全局设置"""
        original_auto_create = settings.AUTO_CREATE_TABLES
        original_enable_debug_pytest = settings.ENABLE_DEBUG_PYTEST
        settings.AUTO_CREATE_TABLES = False  # 测试时禁用主应用当中的自动创建表
        settings.ENABLE_DEBUG_PYTEST = True  # 开启Pytest测试
        yield
        # 还原
        settings.AUTO_CREATE_TABLES = original_auto_create
        settings.ENABLE_DEBUG_PYTEST = original_enable_debug_pytest

    

