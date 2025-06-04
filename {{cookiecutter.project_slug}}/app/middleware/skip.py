import fnmatch
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import logger

class SkipPathMiddleware(BaseHTTPMiddleware):
    """
    使用 fnmatch 支持通配符匹配，比如:
        "/api/v1/prompts/**" 会匹配所有 prompts 下的子路径
        "/api/v1/heroes/*" 会匹配 heroes 下的一级路径
    """
    def __init__(self, app, skip_paths: list):
        super().__init__(app)
        self.skip_paths = skip_paths

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        logger.info(f"请求路径: {path}")
        for skip_path in self.skip_paths:
            if fnmatch.fnmatch(path, skip_path):
                logger.info(f"路径 {path} 被中间件跳过匹配规则: {skip_path}")
                request.state.skip_next_middlewares = True
                break

        return await call_next(request)
