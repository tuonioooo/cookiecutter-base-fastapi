import logging
from typing import List
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logger import logger
from app.core.config import settings
from .skip import SkipPathMiddleware
from app.api import (api_router, v1_router, hero)  # 修改为引入api_router


def setup_middlewares(app: FastAPI) -> None:
    """
    设置所有中间件
    Args:
        app: FastAPI应用实例
    """
    if settings.ENABLE_DEBUG_PYTEST:
        # PYTEST测试环境-跳过验证路径权限列表
        skip_paths = [
             "/docs", "/", "/openapi.json", "/favicon.ico",
            # 示例api
            *get_paths(v1_router, hero.router),
        ]
    else:
        # 生产环境-跳过验证路径权限列表
        skip_paths = [
            #基本
            "/docs", "/", "/openapi.json", "/favicon.ico",
            # 示例api
            *get_paths(v1_router, hero.router),
        ]
    # 中间件顺序类似堆栈，从后往前执行 SkipPathMiddleware->APIKeyMiddleware->ContentSanitizerMiddleware->setup_rate_limit_middleware
    # 添加内容净化中间件    todo
    # 添加api_key验证中间件 todo
    # 添加skip中间件
    app.add_middleware(SkipPathMiddleware, skip_paths=skip_paths)
    # 设置CORS中间件
    setup_cors_middleware(app)
    # 在此处添加其他中间件
    # setup_gzip_middleware(app)
    # setup_https_redirect_middleware(app)
    # 等等...


def setup_cors_middleware(app: FastAPI) -> None:
    """
    设置CORS中间件

    Args:
        app: FastAPI应用实例
    """
    if settings.all_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.all_cors_origins,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )


def get_paths(version_router: str, bi_router: APIRouter) -> List[str]:
    """
    生成动态的路由映射路径列表
    
    Args:
        base_prefix: 基础路径前缀 (如 "/api/v1")
        routers: 路由器列表
    
    Returns:
        包含完整路径的列表
    """
    return [
          f"{api_router.prefix}{version_router.prefix}{bi_router.prefix}/**",
          f"{api_router.prefix}{version_router.prefix}{bi_router.prefix}"
          ]
