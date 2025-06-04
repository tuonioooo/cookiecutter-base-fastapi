from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import ResponseValidationError as FastAPIResponseValidationError
from .logger import logger
from .exceptions import EntityNotFoundError, BusinessException, ResponseValidationError
from .response import fail


# 处理自定义异常
async def business_exception_handler(request: Request, exc: BusinessException):
    logger.error(f"应用异常: {exc.detail}")
    return fail(
        status_code=exc.status_code,
        msg=exc.detail,
    )


# 处理 HTTP 异常
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP 异常: {exc.detail}")
    return fail(
        status_code=exc.status_code,
        msg=exc.detail,
    )


# 处理FastAPI内置的响应验证异常
async def fastapi_response_validation_error_handler(request: Request, exc: FastAPIResponseValidationError):
    # 格式化错误详情
    error_details = []
    for error in exc.errors():
        error_details.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })

    logger.error(f"FastAPI响应验证异常: {error_details}")

    return JSONResponse(
        status_code=422,  # 使用标准的验证错误状态码
        content={
            "message": "响应数据验证失败",
            "detail": error_details,
            "type": "fastapi_response_validation_error"
        }
    )

