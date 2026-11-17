import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        """功能：将日志事件与允许的追踪字段格式化为 JSON。

        输入：self：格式器；record：LogRecord，调用方须避免在事件消息中写入敏感信息。
        输出：str：含 UTC 时间、级别、事件及白名单字段的 JSON，不附加异常堆栈。
        """
        data = {
            "time": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for key in ("request_id", "run_id", "status", "elapsed_ms", "error_type"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data, ensure_ascii=False)


def configure_logging() -> None:
    """功能：为 support_agent 日志器安装唯一的 JSON 标准错误输出处理器。

    输入：无显式参数；使用进程内 support_agent 日志器。
    输出：None；设置 INFO 级别并关闭向父日志器传播，可重复调用。
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("support_agent")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
