import logging

from xwlb.logging_setup import setup_logging
from xwlb import config as cfg
from xwlb.utils import get_yesterday_url
from xwlb.jina_reader import read_webpage_with_jina
from xwlb.notion_client_ext import save_to_notion
from xwlb.mailer import send_email
from xwlb.notifications import send_error_notification
from xwlb.gemini_client import summarize_with_gemini


def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    try:
        # 环境变量检查：根据 REQUIRED_VARS 名称到 cfg 模块查值
        missing_vars = [var for var in cfg.REQUIRED_VARS if not getattr(cfg, var, None)]
        if missing_vars:
            logger.error(f"缺少以下环境变量: {', '.join(missing_vars)}")
            return

        url, title = get_yesterday_url()
        logger.info("获取URL中")

        result = read_webpage_with_jina(url)
        if not result or "data" not in result or "content" not in result["data"]:
            logger.error("无法获取网页内容")
            return

        content = result["data"]["content"]
        logger.info(f"成功获取内容，长度: {len(content)} 字符")

        try:
            summary = summarize_with_gemini(content)
            logger.info(f"成功生成摘要，长度: {len(summary)} 字符")
        except Exception as e:
            import traceback
            error_str = str(e)
            if "RetryError" in error_str or "已重试3次仍失败" in error_str:
                log_details = (
                    f"Gemini API重试3次后仍然失败\n模型: gemini-2.5-flash\nAPI密钥: {cfg.GEMINI_API_KEY[:10]}...****\n"
                    f"内容长度: {len(content)} 字符\n完整错误: {traceback.format_exc()}"
                )
                send_error_notification("重试失败", "Gemini API摘要生成重试3次后仍然失败", "Gemini AI", log_info=log_details)
            logger.error(f"生成摘要失败，将跳过摘要步骤: {error_str}")
            summary = "由于Gemini API不稳定，无法生成摘要。请稍后重试。"

        page_id = save_to_notion(title, content, summary)
        if page_id:
            logger.info("成功保存到Notion！")
        else:
            logger.warning("保存到Notion失败")

        try:
            email_sent = send_email(title, summary, content)
            if email_sent:
                logger.info("成功发送邮件")
            else:
                logger.warning("发送邮件失败")
        except Exception as e:
            import traceback
            error_str = str(e)
            if "生成HTML笔记失败" in error_str:
                log_details = f"HTML笔记生成重试失败\n模型: gemini-2.5-pro\n完整错误: {traceback.format_exc()}"
                send_error_notification("HTML笔记生成失败", "邮件中的HTML笔记生成失败", "Gemini AI", log_info=log_details)
            logger.error(f"发送邮件过程中出错: {error_str}")

    except Exception as e:
        import traceback
        logger.error(f"处理过程中发生错误: {str(e)}")
        error_msg = f"新闻联播程序运行失败: {str(e)}"
        log_details = (
            f"完整错误堆栈: {traceback.format_exc()}\n\n环境变量状态:\n"
            f"- JINA_API_KEY: {'已设置' if cfg.JINA_API_KEY else '未设置'}\n"
            f"- GEMINI_API_KEY: {'已设置' if cfg.GEMINI_API_KEY else '未设置'}\n"
            f"- NOTION_API_KEY: {'已设置' if cfg.NOTION_API_KEY else '未设置'}\n"
            f"- EMAIL配置: {'已设置' if cfg.EMAIL_ADDRESS and cfg.EMAIL_PASSWORD else '未设置'}"
        )
        send_error_notification("程序运行错误", error_msg, "新闻联播自动化系统", log_info=log_details)
    finally:
        logger.info("处理完成")


if __name__ == "__main__":
    logging.getLogger(__name__).info("开始运行新闻联播摘要生成程序")
    main()


