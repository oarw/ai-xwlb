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

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_html_notes(content, title):
    """使用Google Gemini API生成HTML格式的笔记"""
    prompt = f"""
    请将以下新闻联播内容转换为学习笔记形式，重点关注与考研和考公考试相关的内容。

    请生成HTML格式的笔记，包含以下部分：
    1. 标题部分：大标题样式的"{title}"
    2. 整体摘要部分：简洁概括新闻重点
    3. 关键新闻点部分：使用编号列表呈现主要新闻内容
    4. 考研考公重要信息部分：使用醒目的样式标注与国家政策、经济发展、社会治理、重大事件、国际关系等相关内容
    5. 可能考点部分：分析此次新闻内容可能出现的考点，使用表格形式展示
    6. 结合往年考研/考公真题，可进行网络搜索
    7. 对于考公，说明对申论的用法，比如：用来融入申论写作，提供素材等等

    使用适当的HTML标签和CSS样式使内容美观易读，包括但不限于：
    - 使用不同颜色标注不同重要程度的内容
    - 使用合理的字体大小和间距
    - 添加适当的分割线或其他视觉元素
    
    注意：你的返回内容，只需要严格包含html语法内容，不需要有其他解释之类的东西
    新闻内容:
    {content}
    """
    
    try:
        logger.info("正在使用Google Gemini生成HTML笔记")
        # 配置Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        # 创建模型
        model = genai.GenerativeModel('gemini-2.0-flash')
        # 生成回复
        response = model.generate_content(prompt)
        # 返回文本内容
        return response.text
    except Exception as e:
        logger.error(f"生成HTML笔记失败: {str(e)}")
        # 如果失败，返回简单的HTML格式
        return f"""
        <h1>{title}</h1>
        <p>抱歉，无法生成结构化笔记，请查看以下摘要：</p>
        <pre>{content[:500]}...</pre>
        """

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

def send_email(title, summary, content=None):
    """发送HTML格式的笔记摘要邮件"""
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = f"【新闻联播学习笔记】{title}"
    
    # 先生成HTML格式笔记
    html_notes = generate_html_notes(content or summary, title)
    
    # 添加CSS样式的基础HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - 学习笔记</title>
        <style>
            body {{
                font-family: 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background-color: #f9f9f9;
                border-radius: 8px;
                padding: 25px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 2px solid #e0e0e0;
            }}
            .footer {{
                font-size: 12px;
                color: #888;
                text-align: center;
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #e0e0e0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                padding: 10px;
                border: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background-color: #f0f0f0;
            }}
            .important {{
                color: #d32f2f;
                font-weight: bold;
            }}
            .highlight {{
                background-color: #fff9c4;
                padding: 2px 4px;
                border-radius: 3px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {html_notes}
            
            <div class="footer">
                此邮件由AI自动生成，内容仅供参考学习使用。<br>
                如需了解更多详情，请查看完整新闻内容。
            </div>
        </div>
    </body>
    </html>
    """
    
    # 同时添加纯文本版本作为备用
    text_content = f"""
    {title} - 学习笔记
    
    {summary}
    
    ------
    此邮件由自动化系统发送，请勿回复。
    """
    
    # 添加纯文本和HTML两个部分
    part1 = MIMEText(text_content, 'plain', 'utf-8')
    part2 = MIMEText(html_content, 'html', 'utf-8')
    
    msg.attach(part1)
    msg.attach(part2)  # HTML版本会被大多数邮件客户端优先显示
    
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.mailersend.net")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    
    try:
        logger.info(f"正在发送HTML邮件到: {RECIPIENT_EMAIL}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAIL, text)
        server.quit()
        logger.info("HTML邮件发送成功")
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
        email_sent = send_email(title, summary, content)
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
