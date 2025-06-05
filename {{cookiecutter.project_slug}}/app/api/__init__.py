from fastapi import APIRouter

from app.api import (hero)

# 创建API路由器
api_router = APIRouter(prefix="/api")

# 创建版本路由器
router = APIRouter()
v1_router = APIRouter(prefix="/v1")
v2_router = APIRouter(prefix="/v2")

# 注册现有路由
v1_router.include_router(hero.router)

# 注册v1的路由
api_router.include_router(v1_router)


__all__ = ["router", "v1_router", "v2_router", "api_router"]
