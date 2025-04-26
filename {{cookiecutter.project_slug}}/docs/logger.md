# core/logger.py 讲解

这个日志配置模块实现了一个功能完整的日志系统，包括彩色控制台输出和文件日志记录功能。

## 整体功能概述

1. 控制台彩色日志输出
2. 按时间自动分割的日志文件（每天一个文件）
3. 按大小自动分割的日志文件（10MB一个文件）
4. 统一的日志格式
5. Uvicorn 日志接管功能

## 日志文件配置

系统配置了两种类型的文件日志处理：

### 1. 按时间分割（TimedRotatingFileHandler）
- 文件名：`app_time.log`
- 分割规则：每天午夜（midnight）自动分割
- 保留时长：保留最近7天的日志文件
- 文件命名：`app_time.log.YYYY-MM-DD`

### 2. 按大小分割（RotatingFileHandler）
- 文件名：`app_size.log`
- 分割规则：当文件达到10MB时自动分割
- 保留数量：保留最近7个文件
- 编码方式：UTF-8

## `ColoredFormatter`

`ColoredFormatter` 配置是一个高级的 Python 日志格式化设置，主要用于在终端输出带颜色的结构化日志。以下是详细解读：

**1. 核心参数解析**
```python
fmt='%(log_color)s%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s%(reset)s'
```
• `%(log_color)s`：根据日志级别自动应用颜色（由 `log_colors` 配置）。

• `%(asctime)s.%(msecs)03d`：时间戳（精确到毫秒），例如 `2025-04-25 14:30:45.123`。

• `%(levelname)-8s`：日志级别名称（左对齐，固定宽度 8 字符），如 `INFO    `。

• `%(name)s:%(funcName)s:%(lineno)d`：日志来源（模块名:函数名:行号）。

• `%(message)s`：日志正文内容。

• `%(reset)s`：重置颜色，避免后续文本继承颜色。


**2. 颜色配置**
```python
log_colors=log_colors_config,
secondary_log_colors={
    'message': {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_white'
    }
}
```
• 主颜色 (`log_colors`)：控制日志级别字段的颜色（需在 `fmt` 中使用 `%(log_color)s`）。

• 辅助颜色 (`secondary_log_colors`)：独立控制 `%(message)s` 的颜色（需在 `fmt` 中使用 `%(message_log_color)s`）。  

  • 例如：`CRITICAL` 级别的消息会显示为 红色文字 + 白色背景。


**3. 输出示例**
假设日志级别为 `ERROR`，输出效果类似：
```
2025-04-25 14:30:45.123 | ERROR    | module:func:42 - 数据库连接失败
```
• 颜色表现：

  • 时间戳、级别、来源等字段：红色（`ERROR` 级别的主颜色）。

  • 消息正文 `数据库连接失败`：红色（`secondary_log_colors` 中 `ERROR` 的配置）。


**4. 关键特性**
• 多级颜色控制：通过 `secondary_log_colors` 实现消息正文与日志级别的颜色分离。

• 精确时间戳：`%(msecs)03d` 提供毫秒级精度。

• 结构化输出：通过 `%(name)s:%(funcName)s:%(lineno)d` 快速定位代码位置。


**5. 注意事项**
• 终端兼容性：确保终端支持 ANSI 颜色转义码（如 Linux/Mac 终端、Windows Terminal）。

• 文件日志：需禁用颜色（颜色代码会显示为乱码），建议单独配置文件 Handler。


如需进一步调整颜色或格式，可参考 `colorlog` 的[官方文档](https://pypi.org/project/colorlog/)。

## 日志级别控制

日志级别通过配置文件控制，支持：
- DEBUG：调试信息
- INFO：一般信息
- WARNING：警告信息
- ERROR：错误信息
- CRITICAL：严重错误信息

通过 `settings.LOG_LEVEL` 配置，可以动态调整日志输出级别。

## Uvicorn日志接管

通过 `setup_uvicorn_log()` 函数实现对 Uvicorn 日志的接管：
- 接管 `uvicorn`、`uvicorn.error`、`uvicorn.access` 三个日志器
- 清除原有处理器，统一使用项目的日志配置
- 开启日志传播，使 Uvicorn 日志统一通过 root logger 处理

## 日志存储目录

- 日志文件统一存储在项目根目录下的 `logs` 文件夹中
- 目录不存在时会自动创建
- 路径通过相对路径计算，确保在不同环境下都能正常工作

## 使用示例

```python
from logging import getLogger

logger = getLogger(__name__)

# 不同级别的日志使用
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误信息")
```

## 配置调整

如需调整日志配置，可以修改以下参数：
- LOG_LEVEL：通过 settings 配置文件调整日志级别
- maxBytes：文件大小分割阈值（当前10MB）
- backupCount：日志文件保留数量（当前7个）
- 日志格式：可以通过修改 formatter 的 fmt 参数调整