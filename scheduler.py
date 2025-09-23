import schedule
import time
import logging
from xwlb.logging_setup import setup_logging
from app_main import main

setup_logging()
logger = logging.getLogger(__name__)


def run_xwlb_daily():
    """运行新闻联播摘要生成脚本"""
    logger.info("开始执行新闻联播摘要生成任务")
    try:
        main()
        logger.info("新闻联播摘要生成任务执行完成")
    except Exception as e:
        logger.error(f"新闻联播摘要生成任务执行失败: {str(e)}")


if __name__ == "__main__":
    schedule.every().day.at("09:00").do(run_xwlb_daily)
    logger.info("调度器已启动，将在每天上午9点执行新闻联播摘要任务")
    run_xwlb_daily()
    while True:
        schedule.run_pending()
        time.sleep(60)
