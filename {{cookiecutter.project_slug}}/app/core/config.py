import secrets
import warnings
from typing import Annotated, Any, Literal, Dict

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


# CORS配置解析函数
def parse_cors(v: Any) -> list[str] | str:
    """
    解析CORS配置，支持字符串（逗号分隔）或列表格式

    Args:
        v: 输入的CORS配置，可以是字符串或列表

    Returns:
        解析后的CORS源列表或原始字符串

    Raises:
        ValueError: 当输入不是有效的CORS配置格式时
    """
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    """
    应用程序配置设置类

    使用Pydantic BaseSettings管理应用程序配置，支持从环境变量和.env文件加载配置
    """

    # 基本配置
    model_config = SettingsConfigDict(
        # 使用顶级.env文件（位于./app/上一级目录）
        env_file=".env",
        env_ignore_empty=True,  # 忽略空环境变量
        extra="ignore",  # 忽略未定义的额外环境变量
    )

    # BaseSettings 会自动从 .env 文件中读取环境变量。只要你的 .env 文件包含一个名为 LOG_LEVEL 的环境变量，
    # Pydantic 会自动将它读取并赋值给 Settings 类的 LOG_LEVEL 字段。
    LOG_LEVEL: str = "INFO"
    
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"  # 运行环境


    # CORS中间件配置
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # 项目基本信息
    PROJECT_NAME: str = "fastapi-template"  # 项目名称，必须在环境变量中提供
    SENTRY_DSN: HttpUrl | None = None  # Sentry错误追踪服务地址，可选

    





# 实例化配置对象，供应用程序其他部分使用
settings = Settings()  # type: ignore
