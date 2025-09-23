import logging
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from . import config as cfg
from .notifications import send_error_notification

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def read_webpage_with_jina(url):
    """使用 Jina AI 的 Reader API 读取网页内容。"""
    headers = {
        "Authorization": f"Bearer {cfg.JINA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"url": url}

    try:
        logger.info("正在使用Jina AI读取网页内容")
        response = requests.post("https://r.jina.ai/", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        if "data" not in result or "content" not in result.get("data", {}):
            error_msg = f"Jina AI返回格式异常：{result}"
            logger.error(error_msg)
            send_error_notification("响应格式异常", error_msg, "Jina AI", log_info=f"请求URL: {url}\n返回结果: {result}")
            raise Exception(error_msg)
        return result
    except requests.exceptions.HTTPError as e:
        import traceback
        log_details = (
            f"请求URL: {url}\n请求头: {headers}\n请求体: {payload}\n响应状态码: {e.response.status_code}\n"
            f"响应内容: {e.response.text if hasattr(e.response, 'text') else 'N/A'}\n完整错误: {traceback.format_exc()}"
        )
        if e.response.status_code == 401:
            send_error_notification("API密钥失效", f"HTTP 401: {str(e)}", "Jina AI", log_info=log_details)
        elif e.response.status_code == 403:
            send_error_notification("访问被拒绝", f"HTTP 403: {str(e)}", "Jina AI", log_info=log_details)
        elif e.response.status_code == 429:
            send_error_notification("请求频率超限", f"HTTP 429: {str(e)}", "Jina AI", log_info=log_details)
        else:
            send_error_notification("API请求失败", str(e), "Jina AI", log_info=log_details)
        raise
    except Exception as e:
        import traceback
        error_msg = f"读取网页内容失败: {str(e)}"
        logger.error(error_msg)
        if "API" in str(e) or "auth" in str(e).lower() or "key" in str(e).lower():
            log_details = (
                f"请求URL: {url}\n请求头: {headers}\n请求体: {payload}\n完整错误: {traceback.format_exc()}"
            )
            send_error_notification("未知API错误", str(e), "Jina AI", log_info=log_details)
        raise


