from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends
from redis.asyncio import Redis
from .logger import logger

from .config import settings


class RedisClient:
    """Redis客户端封装类"""

    def __init__(self):
        """初始化Redis客户端"""
        self.redis = None
        self._initialized = False

    async def connect(self):
        """确保Redis连接已初始化"""
        if not self._initialized:
            self.redis = redis.Redis.from_url(
                settings.redis_uri,
                decode_responses=True,
                max_connections=10
            )
            try:
                await self.redis.ping()  # 确保 Redis 已连接
                self._initialized = True
            except Exception as e:
                self.redis = None
                raise ConnectionError(f"Failed to connect to Redis: {str(e)}")

    async def close(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
        self._initialized = False

    async def get(self, key):
        """获取键值"""
        if not self._initialized:
            await self.connect()
        return await self.redis.get(key)

    async def set(self, key, value, expire=None, nx=None, ex=None):
        """
        设置键值，支持更多Redis原生参数

        Args:
            key: 键名
            value: 键值
            expire: 过期时间（秒），向后兼容参数
            nx: 仅在键不存在时设置
            ex: 过期时间（秒）

        Returns:
            执行结果
        """
        if not self._initialized:
            await self.connect()

        # 为了兼容现有代码，将expire映射到ex
        if expire is not None and ex is None:
            ex = expire

        return await self.redis.set(key, value, nx=nx, ex=ex)

    async def delete(self, key):
        """删除键"""
        if not self._initialized:
            await self.connect()
        await self.redis.delete(key)

    async def info(self, section=None):
        """获取Redis服务器信息"""
        if not self._initialized:
            await self.connect()
        return await self.redis.info(section)

    def __getattr__(self, name):
        """
        支持访问Redis原生命令
        注意: 此方法返回的是一个代理函数，需要使用await调用
        用法: await redis_client.some_redis_command(args)
        """
        # 获取Redis原生方法
        redis_attr = None
        if self.redis is None:
            # 需要先连接Redis
            async def _proxy_method(*args, **kwargs):
                # 延迟初始化
                await self.connect()
                real_method = getattr(self.redis, name)
                return await real_method(*args, **kwargs)

            return _proxy_method
        else:
            # Redis客户端已初始化
            redis_attr = getattr(self.redis, name)

            # 如果是异步方法，创建代理
            if callable(redis_attr):
                async def _proxy_method(*args, **kwargs):
                    # 确保连接存在
                    if not self._initialized:
                        await self.connect()
                    real_method = getattr(self.redis, name)
                    return await real_method(*args, **kwargs)

                return _proxy_method
            else:
                # 返回普通属性
                return redis_attr


# 全局单例 redis_client
redis_client = RedisClient()


# FastAPI 依赖注入方式，直接复用 redis_client
async def get_redis():
    await redis_client.connect()  # 确保连接已初始化
    return redis_client


# 作为全局的参数依赖注入, 参数入口声明示例 redis: redis_annotated_dep
RedisAnnotatedDep = Annotated[RedisClient, Depends(get_redis)]
