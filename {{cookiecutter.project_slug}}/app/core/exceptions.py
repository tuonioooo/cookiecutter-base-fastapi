from typing import Any
from fastapi import HTTPException, status


class BusinessException(HTTPException):
    """
    业务异常基类
    """

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class EntityNotFoundError(BusinessException):
    """
    实体未找到异常
    """

    def __init__(self, entity_name: str, entity_id: str):
        detail = f"ID为 '{entity_id}' 的 {entity_name} 不存在"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class VersionConflictError(BusinessException):
    def __init__(self, entity_name: str, entity_id: Any):
        detail = f"{entity_name} (ID: {entity_id}) has been modified by another transaction"
        super().__init__(detail, status_code=409)


class DatabaseOperationError(BusinessException):
    def __init__(self, operation: str, details: str = ""):
        detail = f"Database operation '{operation}' failed"
        if details:
            detail += f": {details}"
        super().__init__(detail, status_code=500)


class InvalidInputError(BusinessException):
    def __init__(self, field: str, value: str):
        detail = f"Invalid input for field '{field}': {value}"
        super().__init__(detail, status_code=422)


class ResponseValidationError(BusinessException):
    """
    响应验证异常
    用于处理响应数据格式、内容验证失败的情况
    """
    
    def __init__(self, detail: str = "响应数据验证失败", status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY):
        super().__init__(detail=detail, status_code=status_code)
