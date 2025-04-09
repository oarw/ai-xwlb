import logging
from dotenv import load_dotenv
from xwlb_daily import main

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("开始测试运行新闻联播摘要生成程序")
    main()
    logger.info("测试运行完成")
