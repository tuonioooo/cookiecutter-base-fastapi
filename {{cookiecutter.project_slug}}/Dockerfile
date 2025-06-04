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

COPY requirements.txt requirements-dev.txt ./

# 先检查文件是否存在，不存在则退出并报错
RUN if [ ! -f "requirements.txt" ] || [ ! -f "requirements-dev.txt" ]; then \
        echo "Error: Missing requirements file(s)"; \
        exit 1; \
    fi

# 安装系统依赖（构建+运行时）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# 安装现代 Python 工具链（uv）
# 安装依赖需添加 --system 参数避免自动创建虚拟环境，本身已经是容器环境无效在创建虚拟环境
RUN pip install --upgrade pip && \
    pip install uv==${UV_VERSION} && \
    uv pip install --system -r requirements.txt

# ----------------------------
# 生产阶段构建
# ----------------------------
FROM base AS production

ARG WORKDIR=/fastapi-app

WORKDIR ${WORKDIR}

# 定义非 root 用户名和 UID/GID
# 这里的 UID 和 GID 是为了避免和宿主机冲突，建议使用 1000 以上的 UID/GID
ARG USER_NAME=appuser
ARG USER_UID=1001
ARG USER_GID=1001

# 创建用户和组并授予权限
RUN groupadd -g ${USER_GID} ${USER_NAME} && \
    useradd -m -u ${USER_UID} -g ${USER_GID} ${USER_NAME} && \
    chown -R ${USER_UID}:${USER_GID} ${WORKDIR}

# 设置非 root 用户
USER ${USER_NAME}

# 从builder复制已安装的包并强制转移所有全
# 显式复制可执行文件
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/  
COPY --from=builder --chown=${USER_UID}:${USER_GID} /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# 复制应用代码
COPY --chown=${USER_UID}:${USER_GID} . .


ENV PYTHONPATH="${PYTHONPATH}:/app:${WORKDIR}:."


# 轻量级的健康检查
HEALTHCHECK --interval=30s --timeout=3s \
    CMD ["sh", "-c", "curl -f http://localhost:${APP_PORT:-8000}/health || exit 1"]

EXPOSE 8000

# 设置 uvicorn 启动命令
# 静态写法
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 
# 通过 sh -c 执行命令，会启动一个 shell 子进程来解析和执行命令会多一层 shell 进程开销（可以忽略不计很小）
CMD ["/bin/sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${APP_PORT:-8000}"]
