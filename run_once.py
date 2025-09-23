import logging
from xwlb.logging_setup import setup_logging
from app_main import main

setup_logging()
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("开始测试运行新闻联播摘要生成程序")
    main()
    logger.info("测试运行完成")
