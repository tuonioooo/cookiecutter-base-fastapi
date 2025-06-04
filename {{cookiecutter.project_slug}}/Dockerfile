# ----------------------------
# 第一阶段：基础环境  
# ----------------------------
{% if cookiecutter.python_version == '3.11' -%} 
FROM python:3.11.12-slim-bookworm AS base 
{%- endif %}
{% if cookiecutter.python_version == '3.12' -%} 
FROM python:3.12.10-slim-bookworm AS base 
{%- endif %}

# 全局环境变量，多阶段共享
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_VERSION=0.6.9 \
    LANG=C.UTF-8

# ----------------------------
# 第二阶段：构建环境   
# ----------------------------
FROM base AS builder

WORKDIR /app

# 安装系统依赖（构建时需要的依赖）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# 复制依赖文件（利用Docker缓存层）
COPY uv.linux.lock ./

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install uv==${UV_VERSION} && \
    uv pip sync --system uv.linux.lock

# ----------------------------
# 生产阶段构建
# ----------------------------
FROM base AS production

ARG WORKDIR=/{{cookiecutter.project_slug}}
ARG USER_NAME=appuser
ARG USER_UID=1001
ARG USER_GID=1001

WORKDIR ${WORKDIR}

# 安装生产环境必需的运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# 创建用户和组
RUN groupadd -g ${USER_GID} ${USER_NAME} && \
    useradd -m -u ${USER_UID} -g ${USER_GID} -s /bin/bash ${USER_NAME}

# 从builder复制已安装的Python包和可执行文件
COPY --from=builder /usr/local/lib/python{{cookiecutter.python_version}}/site-packages /usr/local/lib/python{{cookiecutter.python_version}}/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# 复制应用代码并设置权限
COPY --chown=${USER_UID}:${USER_GID} ./app ./app
COPY --chown=${USER_UID}:${USER_GID} ./.env ./.env

# 设置目录权限
RUN chown -R ${USER_UID}:${USER_GID} ${WORKDIR}

# 切换到非root用户
USER ${USER_NAME}

# 设置环境变量
ENV PYTHONPATH="${PYTHONPATH}:${WORKDIR}:."

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT:-8000}/health || exit 1

EXPOSE 8000

# 启动命令 - 直接使用exec形式避免shell包装
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT:-8000}"]