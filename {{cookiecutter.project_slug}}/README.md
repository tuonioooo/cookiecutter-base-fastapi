# FastAPI Base Template

一个基于FastAPI的基础项目模板，提供了完整的项目结构、日志配置、环境变量管理和API示例。

## 特性

- 🚀 基于FastAPI的高性能API框架
- 📝 结构化的日志系统（支持彩色控制台输出、文件滚动存储）
- ⚙️ 基于pydantic-settings的配置管理
- 🔍 完整的REST API示例（英雄API的CRUD操作）
- 🐳 完整的Docker、Docker Compose支持

## 项目结构

```
├── app
│   ├── api                 # API路由模块
│   │   └── hero.py         # 英雄管理API示例
│   ├── core                # 核心功能模块
│   │   ├── config.py       # 配置管理
│   │   └── logger.py       # 日志配置
│   ├── models              # 数据模型
│   │   └── hero.py         # 英雄模型示例
│   └── main.py             # 应用入口
├── logs                    # 日志存储目录
├── .env                    # 环境变量文件
├── .gitignore              # git忽略文件
├── .pylintrc               # python语法检测
├── docker-compose.yml      # Docker Compose配置
├── Dockerfile              # Docker构建文件
└── main.py                 # 项目入口文件
└── pyproject.toml          # 项目依赖配置
└── README.md               # 项目功能介绍
└── requirements-dev.txt    # 项目开发依赖配置
└── requirements.txt        # 项目主依赖包配置
└── uv.lock                 # uv.lock版本控制
```

## 快速开始

### 环境要求

- Python 3.11+

### 安装

1. 安装依赖

```bash
# 安装过的可以忽略uv
pip install uv
# 安装主依赖
uv add -r requirements.txt
```

2. 开发依赖：

```bash
uv add -r requirements-dev.txt --optional dev
```

3. 运行应用

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看API文档。


## 依赖包说明

- **fastapi[standard]**: 高性能API框架，包含标准依赖
- **uvicorn**: ASGI服务器，用于运行FastAPI应用
- **pydantic**: 数据验证和设置管理
- **pydantic-settings**: 基于pydantic的配置管理
- **requests**: HTTP客户端库
- **python-dotenv**: 环境变量管理
- **colorlog**: 彩色日志输出支持

### 开发依赖

- **pytest**: 测试框架
- **black**: 代码格式化工具
- **autopep8**: 代码格式化工具
- **ipdb**: 增强调试工具
- **pylint**: 代码静态分析工具

## 主要功能

### 配置管理

通过 `app/core/config.py` 使用 `pydantic-settings` 管理应用配置，支持从环境变量和 `.env` 文件加载配置。

```python
# 示例环境变量（.env文件）
LOG_LEVEL=INFO
PROJECT_NAME=my-fastapi-app
ENVIRONMENT=local
```

### 日志系统

项目集成了强大的日志系统，支持:

- 彩色控制台输出
- 按时间和大小滚动的文件日志
- 可自定义日志级别
- 详细说明：[logger.md](./docs/logger.md)

日志配置在 `app/core/logger.py` 中定义。

### API示例

项目包含一个完整的英雄管理API示例，演示了:

- 资源的CRUD操作
- 查询参数处理
- 请求和响应模型验证
- 错误处理

## Docker支持

* [Dockerfile](./Dockerfile)
* [docker-compose.yml](./docker-compose.yml)

## 开发指南

### 添加新的API路由

1. 在 `app/api` 目录中创建新的路由模块
2. 在 `app/models` 目录中创建相应的数据模型
3. 将路由导入并注册到 `app/main.py`

### 配置日志

可以通过环境变量调整日志级别：

```
LOG_LEVEL=DEBUG
```

支持的日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 贡献

欢迎提交问题和拉取请求！

## 许可

[MIT](LICENSE)
