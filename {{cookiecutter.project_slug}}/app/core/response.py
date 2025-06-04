# core/response.py
from fastapi.responses import JSONResponse
from starlette import status
from fastapi import Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

# 创建模板引擎实例
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


# 统一返回格式
def html_response(data=None, request: Request = None, msg="success", code=0):
    """
    返回HTML响应
    
    Args:
        data: 要传递给模板的数据
        request: FastAPI/Starlette请求对象
        msg: 响应消息
        code: 响应代码
    
    Returns:
        TemplateResponse: 渲染后的HTML响应
    """
    if request is None:
        # 如果没有提供request，无法返回HTML响应，回退到JSON
        return success(data=data, msg=msg, code=code)
        
    return templates.TemplateResponse(
        "response.html",
        {
            "request": request,
            "title": "API Response",
            "code": code,
            "msg": msg,
            "data": data
        }
    )


def html_response_welcome(data=None, request: Request = None):
    """
    返回HTML响应
    
    Args:
        data: 要传递给模板的数据
        request: FastAPI/Starlette请求对象

    Returns:
        TemplateResponse: 渲染后的HTML响应
    """
    if request is None:
        # 如果没有提供request，无法返回HTML响应，回退到JSON
        return success(data=data)

    return templates.TemplateResponse(
        "welcome.html",
        {
            "request": request,
            "title": data["title"] if data else "欢迎访问我们的网站",
            "subtitle": data["subtitle"] if data else "探索无限可能，发现精彩内容。我们致力于为您提供最佳的用户体验和最优质的服务。",
        }
    )


# 统一返回格式
def success(data=None, status_code=status.HTTP_200_OK, msg="success", code=0, return_null=False):
    content = {
        "code": code,
        "msg": msg
    }
    if data or return_null:
        content["data"] = data
    return JSONResponse(status_code=status_code, content=content)


def fail(msg="error", status_code=status.HTTP_200_OK, code=-1):
    return JSONResponse(status_code=status_code, content={"code": code, "msg": msg})
