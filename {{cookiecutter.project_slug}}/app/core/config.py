from pathlib import Path
import secrets
import warnings
from typing import Annotated, Any, Literal, Dict

from pydantic import (
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


# 获取项目根目录（即 .env 所在根目录）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
print(f"项目根目录={ENV_PATH}")

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
        # 使用顶级.env文件（位于./backend/上一级目录）
        env_file=str(ENV_PATH), # 读取默认的配置文件 可以通过 命令行 uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env.prod --reload 覆盖默认配置文件
        env_ignore_empty=True,  # 忽略空环境变量
        env_file_encoding='utf-8',
        extra="ignore",  # 忽略未定义的额外环境变量
    )

    # BaseSettings 会自动从 .env 文件中读取环境变量。只要你的 .env 文件包含一个名为 LOG_LEVEL 的环境变量，
    # Pydantic 会自动将它读取并赋值给 Settings 类的 LOG_LEVEL 字段。

    AUTO_CREATE_TABLES:  bool = False       # 控制是否自动创建表
    ENABLE_DEBUG_PYTEST: bool = False       # 开启Pytest进行测试   
    LOG_LEVEL: str = "INFO"

    SWAGGER_ENABLE: bool | None = None  # 是否启用Swagger文档

    # API配置
    API_V1_STR: str = "/api/v1"  # API路由前缀
    SECRET_KEY: str = secrets.token_urlsafe(32)  # 随机生成密钥用于令牌签名
    # 访问令牌过期时间：60分钟 * 24小时 * 8天 = 8天
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"  # 前端应用地址
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"  # 运行环境

    # CORS配置
    BACKEND_CORS_ORIGINS: Annotated[
        list[str] | str, BeforeValidator(parse_cors)
    ] = ["http://localhost:8000", "http://localhost:3000"]  # 修改默认值
  
    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        """
        获取所有CORS源，包括前端地址
        """
        origins = []
        if isinstance(self.BACKEND_CORS_ORIGINS, list):
            origins.extend(self.BACKEND_CORS_ORIGINS)
        elif isinstance(self.BACKEND_CORS_ORIGINS, str):
            origins.extend([i.strip() for i in self.BACKEND_CORS_ORIGINS.split(",")])
        
        if self.FRONTEND_HOST:
            origins.append(self.FRONTEND_HOST)
            
        return [origin.rstrip("/") for origin in origins]


    # CORS中间件配置
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # 项目基本信息
    PROJECT_NAME: str = {{ cookiecutter.project_name }} # 项目名称，必须在环境变量中提供
    SENTRY_DSN: HttpUrl | None = None  # Sentry错误追踪服务地址，可选

    # 数据库配置

    # 数据库连接池公共的参数配置项
    POOL_SIZE: int = 50         # 连接池大小
    MAX_OVERFLOW: int = 30      # 最大溢出连接数
    POOL_TIMEOUT: int = 30      # 等待连接的最大时间（秒）
    POOL_RECYCLE: int = 3600    # 每小时回收连接

    # PostgreSQL配置
    POSTGRES_SERVER: str = "localhost"  # PostgreSQL服务器地址
    POSTGRES_PORT: int = 5432    # PostgreSQL端口，默认5432
    POSTGRES_USER: str = "postgres"  # PostgreSQL用户名
    POSTGRES_PASSWORD: str = ""    # PostgreSQL密码
    POSTGRES_DB: str = "app"    # PostgreSQL数据库名称

    # SQLite配置
    SQLITE_FILE_NAME: str = "database.db"  # SQLite数据库文件名
    USE_SQLITE: bool = True  # 是否使用SQLite，默认为True以便于开发

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """
        构建SQLAlchemy数据库URI
        """
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",  # 使用psycopg驱动
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLITE_DATABASE_URI(self) -> str:
        """
        构建SQLite数据库URI
        .app/ 表示数据库文件存储在应用程序根目录的 .app 子目录中，通常用于隔离数据文件
        """
        return f"sqlite:///./app/{self.SQLITE_FILE_NAME}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLITE_CONNECT_ARGS(self) -> Dict[str, bool]:
        """
        SQLite连接参数
        """
        return {"check_same_thread": False}
    
    # Mysql 配置
    MYSQL_SERVER: str = "localhost"     # MySQL服务器地址
    MYSQL_PORT: int = 3306              # MySQL端口，默认3306
    MYSQL_USER: str | None = None       # MySQL用户名
    MYSQL_PASSWORD: str | None = None   # MySQL密码
    MYSQL_DB: str | None = None         # MySQL数据库名称

    # 邮件配置
    SMTP_TLS: bool = True  # 是否使用TLS
    SMTP_SSL: bool = False  # 是否使用SSL
    SMTP_PORT: int = 587  # SMTP端口
    SMTP_HOST: str | None = None  # SMTP服务器
    SMTP_USER: str | None = None  # SMTP用户名
    SMTP_PASSWORD: str | None = None  # SMTP密码
    EMAILS_FROM_EMAIL: EmailStr | None = None  # 发件人邮箱
    EMAILS_FROM_NAME: EmailStr | None = None  # 发件人名称

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        """
        设置默认的发件人名称为项目名称
        """
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48  # 密码重置令牌过期小时数

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        """
        检查邮件功能是否已配置启用
        """
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    # 测试和初始账户配置
    EMAIL_TEST_USER: EmailStr = "test@example.com"  # 测试用户邮箱
    FIRST_SUPERUSER: EmailStr = "admin@example.com"  # 初始超级用户邮箱
    FIRST_SUPERUSER_PASSWORD: str = "changethis"  # 初始超级用户密码

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        """
        检查敏感配置是否使用了默认值

        Args:
            var_name: 变量名称
            value: 变量值

        Raises:
            ValueError: 在非本地环境中使用默认值时抛出
        """
        if value == "changethis":
            message = (
                f'配置项 {var_name} 的值是 "changethis", '
                "出于安全考虑，请修改它，至少在部署环境中。"
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        """
        强制检查敏感配置不使用默认值
        """
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self

    # Redis 配置
    REDIS_HOST: str | None = None  # Redis 服务器地址
    REDIS_PORT: int = 6379  # Redis 端口
    REDIS_DB: int = 0  # Redis 数据库编号
    REDIS_PASSWORD: str | None = None  # Redis 密码，默认为 None
    REDIS_USE_SSL: bool = False  # 是否启用 SSL 连接，默认为 False
    REDIS_URL: str | None = ""  # 默认Redis URL redis://localhost:6379/0
    USE_REDIS_RATE_LIMIT: bool = False  # 默认不开启redis限流
    # 限流相关配置
    RATE_LIMIT_PER_MINUTE: int = 60

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_uri(self) -> str:
        """
        自动生成 Redis 连接 URI
        优先使用 REDIS_URL，其次根据配置拼接
        """
        if self.REDIS_URL:
            return self.REDIS_URL

        scheme = "rediss" if self.REDIS_USE_SSL else "redis"
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"{scheme}://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"




# 实例化配置对象，供应用程序其他部分使用
settings = Settings()  # type: ignore
