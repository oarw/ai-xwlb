import schedule
import time
import subprocess
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_xwlb_daily():
    """运行新闻联播摘要生成脚本"""
    logger.info("开始执行新闻联播摘要生成任务")
    try:
        subprocess.run(["python", "xwlb_daily.py"], check=True)
        logger.info("新闻联播摘要生成任务执行完成")
    except subprocess.SubprocessError as e:
        logger.error(f"新闻联播摘要生成任务执行失败: {str(e)}")

if __name__ == "__main__":
    # 设置每天早上9点运行
    schedule.every().day.at("09:00").do(run_xwlb_daily)
    
    logger.info("调度器已启动，将在每天上午9点执行新闻联播摘要任务")
    
    # 首次运行
    run_xwlb_daily()
    
    # 保持程序运行
    while True:
        schedule.run_pending()
        time.sleep(60)
