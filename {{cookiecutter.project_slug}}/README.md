# {{cookiecutter.project_slug}}

基于FastAPI的高性能Web应用项目模板，提供完整的项目结构和开发基础。

## 核心特性

- 📦 完整的项目结构和最佳实践
- 🚀 基于FastAPI的高性能API框架
- 📝 结构化的日志系统（彩色控制台输出、文件滚动存储）
- ⚙️ 基于pydantic-settings的配置管理
- 🗄️ SQLModel/SQLAlchemy ORM数据库支持
- 🔍 完整的REST API示例
- 🐳 Docker和Docker Compose支持

## 项目结构

```
├── app
│   ├── api                 # API路由模块
│   ├── core                # 核心功能模块
│   │   ├── config.py       # 配置管理
│   │   ├── logger.py       # 日志配置
│   │   └── database        # 数据库相关
│   ├── models              # 数据模型
│   ├── middleware          # 中间件
│   └── main.py             # 应用入口
├── scripts                 # 脚本目录
├── tests                   # 测试目录
├── .env.example            # 环境变量示例
├── docker-compose.yml      # Docker Compose配置
├── Dockerfile              # Docker构建文件
├── pyproject.toml          # 项目依赖配置
├── requirements.txt        # 项目依赖
└── requirements-dev.txt    # 开发依赖
```

## 快速开始

### 环境要求

- Python 3.11+

### 安装依赖

#### 手动安装

```bash
# 使用uv安装依赖
pip install uv
# 安装主依赖
uv add -r requirements.txt
# 开发依赖
uv add -r requirements-dev.txt --optional dev
```

#### 脚本安装

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

### 运行应用

```bash
# 激活虚拟环境
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate

# 启动应用
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 编译依赖（生产部署）

```bash
uv pip compile pyproject.toml -o uv.linux.lock
```

访问 http://localhost:8000/docs 查看API文档。

## 主要功能

### 配置管理

通过`app/core/config.py`使用pydantic-settings管理应用配置，支持从环境变量和`.env`文件加载配置。

### 日志系统

集成了强大的日志系统，支持：
- 彩色控制台输出
- 按时间和大小滚动的文件日志
- 可自定义日志级别

### 数据库支持

- 默认使用SQLite，便于开发
- 支持PostgreSQL和MySQL
- 基于SQLModel的ORM支持

### Docker支持

提供完整的Docker和Docker Compose配置，方便部署和开发。

## 开发指南

### 添加新的API路由

1. 在`app/api`目录中创建新的路由模块
2. 在`app/models`目录中创建相应的数据模型
3. 将路由导入并注册到`app/api/__init__.py`

## 许可

[{{cookiecutter.license}}](LICENSE)
