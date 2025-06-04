import asyncio
from contextlib import asynccontextmanager
import os
import sys
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import ResponseValidationError as FastAPIResponseValidationError
 # 在 Windows 上设置事件循环策略
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from app.api import api_router
from .core.exception_handlers import business_exception_handler, http_exception_handler, \
    fastapi_response_validation_error_handler
from .core.exceptions import BusinessException
from .core.logger import setup_uvicorn_log, logger
from app.middleware.middleware import setup_middlewares
from .core.redis import redis_client
from .core.config import settings
from app.core.database.db_manager import cleanup_database_connections, get_db_manager

# 加载 .env 文件
# load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    更优雅、集中管理生命周期逻辑
    """    # 记录启动时间
    start_time = datetime.now()
    logger.info(f"⏰ 服务启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 初始化日志
    setup_uvicorn_log()
    logger.info("🟢 FastAPI 项目启动日志初始化完成！")
    # 创建数据库表
    db_manager = get_db_manager()
    # 根据配置决定是否创建数据库表
    if settings.AUTO_CREATE_TABLES:
        db_manager.create_all()  # 确保数据库表创建
        logger.info("🟢 数据库表创建完成！")
    logger.info("🚀 应用启动，连接 Redis...")
    logger.info(
    "⚙️ %sRedis连接参数 - host: %s, url: %s",
        " ",
        settings.REDIS_HOST,
        settings.REDIS_URL
    )
    await redis_client.connect()  # 启动时连接 Redis
    logger.info("🟢 redis连接成功！")

    logger.info(f"🗄️ 数据库连接: {settings.SQLITE_DATABASE_URI}, 绝对路径为：{os.path.abspath('./app/' + settings.SQLITE_FILE_NAME)}")
    # 计算启动耗时
    elapsed_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"🔥 服务启动成功！启动耗时: {elapsed_time:.2f}秒") 
    
    yield
      # 记录关闭时间
    shutdown_time = datetime.now()
    logger.info("🛑 应用关闭，断开 Redis...")
    await redis_client.close()  # 关闭时释放 Redis
    logger.info("🛑 应用关闭，断开 数据库连接...")
    await cleanup_database_connections()
    logger.info(f"⏰ 服务关闭时间: {shutdown_time.strftime('%Y-%m-%d %H:%M:%S')}")
    # 关闭时执行
    logger.info("已关闭")





def create_app() -> FastAPI:
    app = FastAPI(
                lifespan=lifespan,
                docs_url="/docs" if settings.SWAGGER_ENABLE else None,
                redoc_url=None,
                title="{{ cookiecutter.project_name }}",
                description="{{cookiecutter.project_short_description}}",
                version="1.0.0",
                contact={
                    "name": "{{ cookiecutter.author }}",
                    "email": "{{ cookiecutter.email }}"
                },
                openapi_tags=[
                    {
                        "name": "工具",
                        "description": "工具相关接口"
                    }
                ],
                )

    # 设置所有中间件
    setup_middlewares(app)
    logger.info("⚡ [create_app] 中间件设置完成")

    # 注册api的路由对象
    app.include_router(api_router)
    logger.info("🔗 [create_app] 路由注册完成")

    # 注册异常处理器
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(FastAPIResponseValidationError, fastapi_response_validation_error_handler)





    return app







