import datetime
import requests
import os
import json
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from notion_client import Client
import time
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv
import google.generativeai as genai

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 免费获取您的 Jina AI API 密钥：https://jina.ai/?sui=apikey
JINA_API_KEY = os.environ.get("JINA_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")

def get_yesterday_url():
    """获取前一天的新闻联播URL"""
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    year = yesterday.strftime("%Y")
    month = yesterday.strftime("%m")
    day = yesterday.strftime("%d")
    
    # 构建URL，参考用户提供的示例
    date_part = f"{year}年{month}月{day}日新闻联播文字版"
    encoded_date = urllib.parse.quote(date_part)
    
    url = f"http://mrxwlb.com/{year}/{month}/{day}/{encoded_date}/"
    title = f"{year}年{month}月{day}日新闻联播"
    
    return url, title

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def read_webpage_with_jina(url):
    """使用Jina AI的Reader API读取网页内容"""
    headers = {
        "Authorization": f"Bearer {JINA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "url": url
    }
    
    try:
        logger.info(f"正在使用Jina AI读取网页内容: {url}")
        response = requests.post("https://r.jina.ai/", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"读取网页内容失败: {str(e)}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def summarize_with_gemini(content):
    """使用Google Gemini API总结内容"""
    prompt = f"""
    请总结以下新闻联播内容，特别关注与考研和考公考试相关的重点内容。
    
    请提供:
    1. 整体摘要（200字左右）
    2. 主要新闻点（列表形式）
    3. 考研考公重点：重点标注与国家政策、经济发展、社会治理、重大事件、国际关系等相关的内容
    
    新闻内容:
    {content}
    """
    
    try:
        logger.info("正在使用Google Gemini总结内容")
        # 配置Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        # 创建模型
        model = genai.GenerativeModel('gemini-2.0-flash')
        # 生成回复
        response = model.generate_content(prompt)
        # 返回文本内容
        return response.text
    except Exception as e:
        logger.error(f"生成摘要失败: {str(e)}")
        raise

def get_notion_database_properties():
    """获取Notion数据库的属性结构"""
    try:
        notion = Client(auth=NOTION_API_KEY)
        database = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        logger.info(f"Notion数据库属性: {database['properties'].keys()}")
        return database['properties']
    except Exception as e:
        logger.error(f"获取Notion数据库属性失败: {str(e)}")
        return None

def save_to_notion(title, content, summary):
    """将原文和总结保存到Notion"""
    notion = Client(auth=NOTION_API_KEY)
    
    # 获取数据库属性
    db_properties = get_notion_database_properties()
    if not db_properties:
        logger.error("无法获取Notion数据库属性，保存失败")
        return None
        
    # 找到标题和日期属性的正确名称
    title_property_name = None
    date_property_name = None
    
    for name, prop in db_properties.items():
        if prop['type'] == 'title':
            title_property_name = name
        elif prop['type'] == 'date':
            date_property_name = name
    
    if not title_property_name or not date_property_name:
        logger.error(f"未找到所需属性，标题属性: {title_property_name}, 日期属性: {date_property_name}")
        return None
    
    # 将长内容分割成较小的块
    def chunk_text(text, max_length=2000):
        return [text[i:i+max_length] for i in range(0, len(text), max_length)]
    
    content_chunks = chunk_text(content)
    summary_chunks = chunk_text(summary)
    
    # 构建页面内容
    children = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "摘要"}}]
            }
        }
    ]
    
    # 添加摘要块
    for chunk in summary_chunks:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        })
    
    # 添加原文标题
    children.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "原文"}}]
        }
    })
    
    # 添加原文块
    for chunk in content_chunks:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        })
    
    properties = {}
    properties[title_property_name] = {
        "title": [{"text": {"content": title}}]
    }
    properties[date_property_name] = {
        "date": {"start": datetime.datetime.now().strftime("%Y-%m-%d")}
    }
    
    try:
        logger.info(f"正在保存到Notion: {title}")
        page = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties=properties,
            children=children
        )
        return page["id"]
    except Exception as e:
        logger.error(f"保存到Notion失败: {str(e)}")
        return None

def save_to_notion_direct(title, content, summary):
    """使用直接API调用方式保存到Notion"""
    # 构建页面内容
    blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "摘要"}}]
            }
        }
    ]
    
    # 添加摘要块
    for chunk in chunk_text(summary):
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        })
    
    # 添加原文标题
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": "原文"}}]
        }
    ])
    
    # 添加原文块
    for chunk in chunk_text(content):
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": chunk}}]
            }
        })

    # 构造API请求数据
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "title": {  # 尝试使用"title"作为属性名
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "Date": {  # 尝试使用"Date"作为属性名
                "date": {"start": datetime.datetime.now().strftime("%Y-%m-%d")}
            }
        },
        "children": blocks
    }
    
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    try:
        logger.info(f"正在直接调用API保存到Notion: {title}")
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        logger.info(f"成功保存到Notion，页面ID: {data.get('id')}")
        return data.get('id')
    except Exception as e:
        logger.error(f"直接保存到Notion失败: {str(e)}")
        if isinstance(e, requests.exceptions.HTTPError):
            logger.error(f"API响应: {e.response.text}")
        return None

def send_email(title, summary):
    """发送摘要邮件"""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = f"【新闻联播摘要】{title}"
    
    body = f"""
    {title} 摘要：
    
    {summary}
    
    ------
    此邮件由自动化系统发送，请勿回复。
    """
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        logger.info(f"正在发送邮件到: {RECIPIENT_EMAIL}")
        # 根据您的邮件服务商调整SMTP设置
        server = smtplib.SMTP('smtp.mailersend.net', 587)  # 以Gmail为例
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAIL, text)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {str(e)}")
        return False

def main():
    try:
        # 检查必要的环境变量
        required_vars = ["JINA_API_KEY", "GEMINI_API_KEY", "NOTION_API_KEY", 
                        "NOTION_DATABASE_ID", "EMAIL_ADDRESS", 
                        "EMAIL_PASSWORD", "RECIPIENT_EMAIL"]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            logger.error(f"缺少以下环境变量: {', '.join(missing_vars)}")
            return
        
        # 获取昨天的新闻联播URL
        url, title = get_yesterday_url()
        logger.info(f"获取URL: {url}")
        
        # 使用Jina AI读取网页内容
        result = read_webpage_with_jina(url)
        
        if not result or "data" not in result or "content" not in result["data"]:
            logger.error("无法获取网页内容")
            return
        
        content = result["data"]["content"]
        logger.info(f"成功获取内容，长度: {len(content)} 字符")
        
        # 总结内容
        summary = summarize_with_gemini(content)
        logger.info(f"成功生成摘要，长度: {len(summary)} 字符")
        
        # 保存到Notion
        page_id = save_to_notion(title, content, summary)
        if page_id:
            logger.info(f"成功保存到Notion，页面ID: {page_id}")
        else:
            logger.warning("保存到Notion失败")
        
        # 发送邮件
        email_sent = send_email(title, summary)
        if email_sent:
            logger.info("成功发送邮件")
        else:
            logger.warning("发送邮件失败")
            
    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}")
    finally:
        logger.info("处理完成")

if __name__ == "__main__":
    logger.info("开始运行新闻联播摘要生成程序")
    main()
