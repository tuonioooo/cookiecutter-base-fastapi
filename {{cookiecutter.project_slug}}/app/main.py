from starlette.routing import Match
from fastapi import Response
from starlette.requests import Request

from app.app_factory import create_app  # 修改为引入api_router
from .core.response import fail, html_response_welcome

"""
开发调试期间：
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
或
fastapi dev main.py

启动命令携带环境文件参数：
uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env.prod --reload
启动命令携带环境文件参数：uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env.prod --reload
"""
app = create_app()


@app.middleware("http")
async def middleware_exception_handler(request: Request, call_next):
    """
    中间件异常处理机制（全局定义的异常处理机制是捕获不到的），专门捕获中间件的异常
    """
    try:
        return await call_next(request)
    except Exception as exc:
        return fail(msg=f"{exc}")

@app.get("/")
def read_root(request: Request):
    return html_response_welcome(data={
        "title": "欢迎访问我们的网站",
        "subtitle": "探索无限可能，发现精彩内容。我们致力于为您提供最佳的用户体验和最优质的服务。"
    }, request=request)
