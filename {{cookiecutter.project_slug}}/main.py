from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import logger, setup_uvicorn_log
from app.api.hero import router as hero_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    更优雅、集中管理生命周期逻辑
    """
    # 启动时执行
    # 初始化日志
    setup_uvicorn_log()
    logger.info("🟢 FastAPI 项目启动日志初始化完成！")
    logger.info("🔥 服务启动成功")
    yield
    # 关闭时执行
    logger.info("已关闭")

# 设置应用元数据
# 启动命令：uvicorn main:app --reload  / fastapi dev main.py（开发调试期间）
app = FastAPI(lifespan=lifespan,
              title=settings.PROJECT_NAME,
              description="FastAPI基础模板项目API",
              version="0.1.0",
              contact={
                  "name": "tuonioooo",
                  "email": "daizhaoman@sina.com"
              })


# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 注册路由
app.include_router(hero_router)



@app.get("/")
async def root():
    #from loguru import logger

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")


    return {"message": f"Welcome to {settings.PROJECT_NAME}"}


"""
健康检查接口
"""
@app.get("/health")
def health_check():
    return {"status": "healthy"}