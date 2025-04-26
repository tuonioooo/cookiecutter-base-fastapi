# logger_config.py
import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from colorlog import ColoredFormatter

from app.core.config import settings

# 日志存储目录
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../logs")
os.makedirs(LOG_DIR, exist_ok=True)  # 自动创建目录

# 日志格式
log_colors_config = {  # 颜色配置
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red'
}

formatter = ColoredFormatter(
    fmt='%(log_color)s[%(asctime)s.%(msecs)03d] | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s%(reset)s',
    datefmt='%Y-%m-%d %H:%M:%S',
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
)


# 控制台 Handler添加了colorlog颜色格式化
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# 文件 Handler（每天分割，保留7天）
# 文件命名格式为：app.log.2025-03-14
file_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, "app_time.log"),
    when='midnight',    # 每天午夜分割日志
    interval=1,         # 每天分割
    backupCount=7,      # 7 天，backupCount=7
    encoding='utf-8'    # 指定 UTF-8 编码，避免乱码
)

file_handler.setFormatter(logging.Formatter(
    '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(filename)s:%(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# 日志文件达到 10MB 时分割
# 文件命名的格式为：app_size.log
file_size_handler = RotatingFileHandler(
    filename=os.path.join(LOG_DIR, "app_size.log"),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=7,
    encoding='utf-8'
)


file_size_handler.setFormatter(logging.Formatter(
    '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))


# 获取 root logger
logger = logging.getLogger()
LOG_LEVEL = settings.LOG_LEVEL.upper()      # 通过配置文件读取,你可以调节为 INFO / WARNING
logger.setLevel(getattr(logging, LOG_LEVEL))
# logger.setLevel(logging.INFO)
logger.addHandler(console_handler)  # 添加控制台日志处理器
logger.addHandler(file_handler)     # 添加文件日志处理器
logger.addHandler(file_size_handler)     # 添加文件日志处理器


def setup_uvicorn_log():
    """接管 uvicorn 默认日志"""
    uvicorn_log_config = ["uvicorn", "uvicorn.error", "uvicorn.access"]
    for logger_name in uvicorn_log_config:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()  # 清除原有 handler
        uvicorn_logger.propagate = True  # 让 uvicorn 日志走 root logger

