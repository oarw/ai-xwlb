import logging
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import google.generativeai as genai

from . import config as cfg
from .notifications import send_error_notification

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def summarize_with_gemini(content: str) -> str:
    prompt = f"""
    请总结以下新闻联播内容，特别关注与考研和考公考试相关的重点内容。

    请提供:
    1. 整体摘要（200字左右）
    2. 主要新闻点（列表形式）
    3. 考研考公重点：重点标注与国家政策、经济发展、社会治理、重大事件、国际关系等相关的内容
    4. 根据新闻模仿考研政治，公务员考试（行测、申论、面试）出几道模拟题，说明出题思路，答案解析，举一反三等等
    新闻内容:
    {content}
    """
    try:
        logger.info("正在总结内容")
        genai.configure(api_key=cfg.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        import traceback
        error_str = str(e)
        logger.error(f"生成摘要失败: {error_str}")
        if (
            "500" in error_str
            or "An internal error has occurred" in error_str
            or "UNAVAILABLE" in error_str
        ):
            logger.warning(f"Gemini API服务暂时不可用，将进行重试: {error_str}")
            raise
        log_details = (
            f"模型: gemini-2.5-flash\nAPI密钥: {cfg.GEMINI_API_KEY[:10]}...****\n内容长度: {len(content)} 字符\n"
            f"Prompt长度: {len(prompt)} 字符\n完整错误: {traceback.format_exc()}"
        )
        if "403" in error_str and "CONSUMER_SUSPENDED" in error_str:
            send_error_notification("账户被暂停", "API消费者账户已被暂停", "Gemini AI", log_info=log_details)
        elif "403" in error_str and "Permission denied" in error_str:
            send_error_notification("权限被拒绝", error_str, "Gemini AI", log_info=log_details)
        elif "401" in error_str or "Invalid API key" in error_str:
            send_error_notification("API密钥无效", error_str, "Gemini AI", log_info=log_details)
        elif "429" in error_str or "quota" in error_str.lower():
            send_error_notification("配额超限", error_str, "Gemini AI", log_info=log_details)
        else:
            send_error_notification("未知错误", error_str, "Gemini AI", log_info=log_details)
        raise


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def generate_html_notes(content: str, title: str) -> str:
    prompt = f"""
    **注意：你的返回内容，只需要严格包含html语法内容，需要严格按照html标签语法，不要在html里出现markdown语法形式，更不需要有其他解释之类的东西**
    请将以下新闻联播内容转换为学习笔记形式，重点关注与考研和考公考试相关的内容。

    请生成HTML格式的笔记，包含以下部分：
    1. 标题部分：大标题样式的"{title}"
    2. 整体摘要部分：简洁概括新闻重点（约300字左右）
    3. 关键新闻点部分：使用编号列表呈现主要新闻内容，然后第二行是详细新闻报道
    4. 考研考公重要信息部分：使用醒目的样式标注与国家政策、经济发展、社会治理、重大事件、国际关系等相关内容
    5. 可能考点部分：分析此次新闻内容可能出现的考点，使用表格形式展示，可与下面的第六点相结合
    6. 结合往年考研/考公真题， 根据新闻模仿考研政治和公务员考试（行测、申论、面试）出几道模拟题，**说明出题思路，答案解析，如何得到答案，思考流程是什么，参考答案（必须包含！！），举一反三等等**（必须包含！！）
    7. 对于考公，说明对申论的用法，比如：用来融入申论写作，提供素材等等，请提供详细示例
    8.补充第七条，在下方模仿高分试卷答案写几段申论片段，并说明如何使用今天的新闻
    9.如何简单的记忆需要用到的新闻素材
    10.必须在内容中加入图表总结当天的主要新闻内容来帮助理解和记忆：
    - 使用 HTML <img> 标签嵌入直观的流程图或思维导图
    - 图表应该使用 QuickChart Graphviz API 链接生成
    - 图表URL格式应为：https://quickchart.io/graphviz?graph=digraph{...}
    - 在设计图表时注意以下要点：
      遵守以下规则：

    新闻内容:
    {content}
    """
    try:
        logger.info("正在生成笔记")
        genai.configure(api_key=cfg.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        import traceback
        error_str = str(e)
        logger.error(f"生成HTML笔记失败: {error_str}")
        if (
            "500" in error_str
            or "An internal error has occurred" in error_str
            or "UNAVAILABLE" in error_str
        ):
            logger.warning(f"Gemini API服务暂时不可用，将进行重试: {error_str}")
            raise
        log_details = (
            f"模型: gemini-2.5-pro\nAPI密钥: {cfg.GEMINI_API_KEY[:10]}...****\n内容长度: {len(content)} 字符\n"
            f"Prompt长度: {len(prompt)} 字符\n完整错误: {traceback.format_exc()}"
        )
        if "403" in error_str and "CONSUMER_SUSPENDED" in error_str:
            send_error_notification("账户被暂停", "API消费者账户已被暂停", "Gemini AI", log_info=log_details)
        elif "403" in error_str and "Permission denied" in error_str:
            send_error_notification("权限被拒绝", error_str, "Gemini AI", log_info=log_details)
        elif "401" in error_str or "Invalid API key" in error_str:
            send_error_notification("API密钥无效", error_str, "Gemini AI", log_info=log_details)
        elif "429" in error_str or "quota" in error_str.lower():
            send_error_notification("配额超限", error_str, "Gemini AI", log_info=log_details)
        else:
            send_error_notification("未知错误", error_str, "Gemini AI", log_info=log_details)
        return f"""
        <h1>{title}</h1>
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #856404;">⚠️ 笔记生成失败</h3>
            <p>由于API错误，无法生成结构化笔记。错误信息：{error_str}</p>
            <p>请查看以下原始摘要内容：</p>
        </div>
        <pre style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; white-space: pre-wrap;">{content[:500]}...</pre>
        """


