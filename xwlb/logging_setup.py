import logging


class PrivacyFilter(logging.Filter):
    """在日志中屏蔽或替换敏感信息。"""

    def filter(self, record):
        if hasattr(record, "msg") and isinstance(record.msg, str):
            if "api.notion.com" in record.msg:
                if "GET https://api.notion.com" in record.msg:
                    record.msg = record.msg.replace(
                        "GET https://api.notion.com/v1/databases/***", "GET notion"
                    )
                elif "POST https://api.notion.com" in record.msg:
                    record.msg = record.msg.replace(
                        "POST https://api.notion.com/v1/pages", "POST notion"
                    )
                else:
                    record.msg = record.msg.replace("https://api.notion.com/v1/", "notion/")
        return True


def setup_logging() -> logging.Logger:
    """配置全局日志与隐私过滤。返回当前模块 logger。"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    root_logger = logging.getLogger()
    privacy_filter = PrivacyFilter()
    root_logger.addFilter(privacy_filter)

    # 第三方库日志级别控制
    notion_logger = logging.getLogger("notion_client")
    notion_logger.setLevel(logging.ERROR)
    notion_logger.addFilter(privacy_filter)

    requests_logger = logging.getLogger("requests")
    requests_logger.setLevel(logging.ERROR)

    urllib3_logger = logging.getLogger("urllib3")
    urllib3_logger.setLevel(logging.ERROR)

    http_client_logger = logging.getLogger("notion_client.http_client")
    http_client_logger.setLevel(logging.ERROR)
    http_client_logger.addFilter(privacy_filter)

    return logging.getLogger(__name__)


