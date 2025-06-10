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
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from dotenv import load_dotenv
import google.generativeai as genai

# 加载环境变量
load_dotenv()

# 创建自定义日志过滤器
class PrivacyFilter(logging.Filter):
    def filter(self, record):
        # 检查并修改日志消息中的敏感信息
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            # 替换Notion API URL
            if 'api.notion.com' in record.msg:
                if 'GET https://api.notion.com' in record.msg:
                    record.msg = record.msg.replace('GET https://api.notion.com/v1/databases/***', 'GET notion')
                elif 'POST https://api.notion.com' in record.msg:
                    record.msg = record.msg.replace('POST https://api.notion.com/v1/pages', 'POST notion')
                else:
                    # 对其他Notion API调用的通用处理
                    record.msg = record.msg.replace('https://api.notion.com/v1/', 'notion/')
        return True

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加隐私过滤器
logger.addFilter(PrivacyFilter())

# 更全面地控制notion_client及相关日志
# 设置notion_client库的日志级别
notion_logger = logging.getLogger('notion_client')
notion_logger.setLevel(logging.ERROR)  # 将级别改为ERROR以禁止INFO级别日志
notion_logger.addFilter(PrivacyFilter())

# 同时控制requests和urllib3的日志，因为notion_client使用这些库
requests_logger = logging.getLogger('requests')
requests_logger.setLevel(logging.ERROR)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.ERROR)

# 控制HTTP请求的日志
http_client_logger = logging.getLogger('notion_client.http_client')
http_client_logger.setLevel(logging.ERROR)
http_client_logger.addFilter(PrivacyFilter())

# 免费获取您的 Jina AI API 密钥：https://jina.ai/?sui=apikey
JINA_API_KEY = os.environ.get("JINA_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")
# 添加发件人邮箱环境变量
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")

def send_error_notification(error_type, error_message, api_name, log_info=None):
    """发送API错误通知邮件"""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = f"⚠️ 【API错误通知】{api_name} API异常"
    
    # 添加日志信息部分
    log_section = ""
    if log_info:
        log_section = f"""
        <div class="log-section">
            <h3>🔍 详细日志信息：</h3>
            <pre style="background-color: #f1f3f4; padding: 15px; border-radius: 5px; font-size: 12px; overflow-x: auto; white-space: pre-wrap; border: 1px solid #dadce0;">{log_info}</pre>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API错误通知</title>
        <style>
            body {{
                font-family: 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 700px;
                margin: 0 auto;
                padding: 20px;
            }}
            .container {{
                background-color: #fff5f5;
                border: 2px solid #f56565;
                border-radius: 8px;
                padding: 25px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 2px solid #f56565;
            }}
            .error-title {{
                color: #e53e3e;
                font-size: 24px;
                font-weight: bold;
                margin: 0;
            }}
            .error-info {{
                background-color: #fed7d7;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .log-section {{
                background-color: #f8f9fa;
                border: 1px solid #dadce0;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .timestamp {{
                font-size: 14px;
                color: #666;
                text-align: center;
                margin-top: 20px;
            }}
            .suggestion {{
                background-color: #e6fffa;
                border-left: 4px solid #38b2ac;
                padding: 15px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="error-title">🚨 API 服务异常通知</h1>
            </div>
            
            <div class="error-info">
                <h3>错误详情：</h3>
                <p><strong>API服务：</strong>{api_name}</p>
                <p><strong>错误类型：</strong>{error_type}</p>
                <p><strong>错误信息：</strong>{error_message}</p>
            </div>
            
            {log_section}
            
            <div class="suggestion">
                <h3>🔧 建议处理方案：</h3>
                <ul>
                    <li><strong>API Key失效：</strong>请检查并更新环境变量中的API密钥</li>
                    <li><strong>账户被暂停：</strong>请联系API服务商客服处理</li>
                    <li><strong>配额用尽：</strong>请检查API使用量并考虑升级套餐</li>
                    <li><strong>网络问题：</strong>请检查网络连接状态</li>
                    <li><strong>模型问题：</strong>尝试切换到其他可用的模型版本</li>
                </ul>
            </div>
            
            <div class="timestamp">
                报告时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
    </body>
    </html>
    """
    
    # 文本版本也包含日志信息
    text_log_section = f"\n\n详细日志信息：\n{log_info}" if log_info else ""
    
    text_content = f"""
    API服务异常通知
    
    API服务：{api_name}
    错误类型：{error_type}
    错误信息：{error_message}
    {text_log_section}
    
    建议处理方案：
    1. 检查API密钥是否有效
    2. 检查账户状态
    3. 检查API使用配额
    4. 检查网络连接
    5. 尝试切换模型版本
    
    报告时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    part1 = MIMEText(text_content, 'plain', 'utf-8')
    part2 = MIMEText(html_content, 'html', 'utf-8')
    
    msg.attach(part1)
    msg.attach(part2)
    
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.mailersend.net")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    
    try:
        logger.info(f"正在发送{api_name} API错误通知邮件...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, RECIPIENT_EMAIL, text)
        server.quit()
        logger.info(f"{api_name} API错误通知邮件发送成功")
        return True
    except Exception as e:
        logger.error(f"发送{api_name} API错误通知邮件失败: {str(e)}")
        return False

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
        logger.info(f"正在使用Jina AI读取网页内容")
        response = requests.post("https://r.jina.ai/", headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # 检查Jina AI返回的结果是否成功
        if "data" not in result or "content" not in result.get("data", {}):
            error_msg = f"Jina AI返回格式异常：{result}"
            logger.error(error_msg)
            send_error_notification("响应格式异常", error_msg, "Jina AI", log_info=f"请求URL: {url}\n返回结果: {result}")
            raise Exception(error_msg)
        
        return result
    except requests.exceptions.HTTPError as e:
        import traceback
        log_details = f"请求URL: {url}\n请求头: {headers}\n请求体: {payload}\n响应状态码: {e.response.status_code}\n响应内容: {e.response.text if hasattr(e.response, 'text') else 'N/A'}\n完整错误: {traceback.format_exc()}"
        
        if e.response.status_code == 401:
            error_msg = "Jina AI API密钥无效或已过期"
            logger.error(error_msg)
            send_error_notification("API密钥失效", f"HTTP 401: {str(e)}", "Jina AI", log_info=log_details)
        elif e.response.status_code == 403:
            error_msg = "Jina AI API访问被拒绝，可能账户被暂停"
            logger.error(error_msg)
            send_error_notification("访问被拒绝", f"HTTP 403: {str(e)}", "Jina AI", log_info=log_details)
        elif e.response.status_code == 429:
            error_msg = "Jina AI API请求频率超限"
            logger.error(error_msg)
            send_error_notification("请求频率超限", f"HTTP 429: {str(e)}", "Jina AI", log_info=log_details)
        else:
            error_msg = f"Jina AI API请求失败: {str(e)}"
            logger.error(error_msg)
            send_error_notification("API请求失败", str(e), "Jina AI", log_info=log_details)
        raise
    except Exception as e:
        import traceback
        error_msg = f"读取网页内容失败: {str(e)}"
        logger.error(error_msg)
        if "API" in str(e) or "auth" in str(e).lower() or "key" in str(e).lower():
            log_details = f"请求URL: {url}\n请求头: {headers}\n请求体: {payload}\n完整错误: {traceback.format_exc()}"
            send_error_notification("未知API错误", str(e), "Jina AI", log_info=log_details)
        raise

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def summarize_with_gemini(content):
    """使用Google Gemini API总结内容"""
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
        # 配置Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        # 创建模型
        # model = genai.GenerativeModel('gemini-2.0-flash')
        # model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        model = genai.GenerativeModel('gemini-2.0-flash')
        # 生成回复
        response = model.generate_content(prompt)
        # 返回文本内容
        return response.text
    except Exception as e:
        import traceback
        error_str = str(e)
        logger.error(f"生成摘要失败: {error_str}")
        
        # 对于500错误或服务不可用，让重试机制处理
        if "500" in error_str or "An internal error has occurred" in error_str or "UNAVAILABLE" in error_str:
            logger.warning(f"Gemini API服务暂时不可用，将进行重试: {error_str}")
            raise  # 让retry装饰器重试
        
        # 构建详细日志信息
        log_details = f"模型: gemini-2.5-flash-preview-05-20\nAPI密钥: {GEMINI_API_KEY[:10]}...****\n内容长度: {len(content)} 字符\nPrompt长度: {len(prompt)} 字符\n完整错误: {traceback.format_exc()}"
        
        # 对于其他类型的错误（不会重试的错误），发送通知
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
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def generate_html_notes(content, title):
    """使用Google Gemini API生成HTML格式的笔记"""
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
    - 图表URL格式应为：https://quickchart.io/graphviz?graph=digraph{{...}}
    - 在设计图表时注意以下要点：
      遵守以下规则：

**代码规范**  
1. 属性必须用逗号分隔：`[shape=record, label="数据流"]`  
2. 每个语句单独成行且分号结尾（含子图闭合）🚀  
3. 中文标签不需要空格的地方不要空格  
4. 图表外可以用文字补充回答  

**URL编码**  
1. 空格转%20，保留英文双引号  
2. URL必须是单行（无换行符）  
3. 特殊符号强制编码：  
   - 加号 `+` → `%2B`  
   - 括号 `()` → `%28%29`  
   - 尖括号 `<>` → `%3C%3E`  
   - 百分号 `%` → `%25` 🚀  

**错误预防**  
1. 箭头仅用`->`（禁用→或-%3E等错误格式）  
2. 中文标签必须显式声明：`label="用户登录"`  
3. 节点定义与连线分开书写，禁止合并写法  
4. 每个语句必须分号结尾（含最后一行）💥分号必须在语句末尾而非属性内  
5. 禁止匿名节点（必须显式命名）  
6. 中文标签禁用空格（用%20或下划线替代空格）  
7. 同名节点禁止多父级（需创建副本节点）  
8. 节点名仅限ASCII字符（用label显示中文）🚀  
9. 子图闭合必须加分号：`subgraph cluster1{{...}};` 🚀  

**输出格式**（严格遵循）：  
![流程图](https://quickchart.io/graphviz?graph=digraph{{rankdir=LR;start[shape=box,label="开始"];process[shape=ellipse,label="处理数据"];start->process[label="流程启动"];}})  
### **高频错误自查表**
```graphviz
digraph {{
  // ✅正确示例
  jms[label="詹姆斯·西蒙斯"];  // 🚀ASCII节点名+中文label
  nodeA[shape=box,label="收益率%28年化%29"];  // 🚀括号%28%29+百分号%25
  subgraph cluster1{{label="第一部分";}};  // 🚀子图闭合带分号
  
  // ❌错误示例
  危险节点[label="Python(科学)"];           // 💥括号未编码
  错误基金[label="年化66%"];               // 💥百分号未转义%25
  中文节点名[shape=box];                  // 💥非ASCII节点名
  subgraph cluster2{{label="错误子图"}}    // 💥缺少闭合分号
}}
---



    - 示例：<img src="https://quickchart.io/graphviz?graph=digraph{{rankdir=LR;start[shape=box,label=%22政策要点%22];impact[shape=ellipse,label=%22社会影响%22];start->impact[label=%22导致%22];}}" alt="政策流程图">
    
    
    
    

    使用适当的HTML标签和CSS样式使内容美观易读，包括但不限于：
    - 使用不同颜色标注不同重要程度的内容
    - 使用合理的字体大小和间距
    - 添加适当的分割线或其他视觉元素
    - 可以适当添加一些帮助记忆的交互元素（如果HTML邮件支持的话）
    - 可以在最后添加抽认卡（或称闪卡，anki记忆卡）的形式来帮助记忆本日的内容，正面是问题，点击反面是答案
    
    新闻内容:
    {content}
    """
    
    try:
        logger.info("正在生成笔记")
        # 配置Gemini API
        genai.configure(api_key=GEMINI_API_KEY)
        # 创建模型
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        # 生成回复
        response = model.generate_content(prompt)
        # 返回文本内容
        return response.text
    except Exception as e:
        import traceback
        error_str = str(e)
        logger.error(f"生成HTML笔记失败: {error_str}")
        
        # 对于500错误或服务不可用，让重试机制处理
        if "500" in error_str or "An internal error has occurred" in error_str or "UNAVAILABLE" in error_str:
            logger.warning(f"Gemini API服务暂时不可用，将进行重试: {error_str}")
            raise  # 让retry装饰器重试
        
        # 构建详细日志信息
        log_details = f"模型: gemini-2.5-flash-preview-05-20\nAPI密钥: {GEMINI_API_KEY[:10]}...****\n内容长度: {len(content)} 字符\nPrompt长度: {len(prompt)} 字符\n完整错误: {traceback.format_exc()}"
        
        # 对于其他类型的错误（不会重试的错误），发送通知
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
        
        # 如果失败，返回简单的HTML格式
        return f"""
        <h1>{title}</h1>
        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #856404;">⚠️ 笔记生成失败</h3>
            <p>由于API错误，无法生成结构化笔记。错误信息：{error_str}</p>
            <p>请查看以下原始摘要内容：</p>
        </div>
        <pre style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; white-space: pre-wrap;">{content[:500]}...</pre>
        """

def get_notion_database_properties():
    """获取Notion数据库的属性结构"""
    try:
        notion = Client(auth=NOTION_API_KEY)
        database = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        logger.info(f"已获取Notion数据库属性")
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
        if (prop['type'] == 'title'):
            title_property_name = name
        elif (prop['type'] == 'date'):
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
        logger.info(f"正在保存到Notion")
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
    # 使用环境变量中的发件人地址，而不是硬编码
    msg['From'] = EMAIL_SENDER
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
        logger.info(f"正在发送邮件....")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        # 登录时仍使用环境变量中的凭据
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        # 发送时使用环境变量中的发件人地址
        server.sendmail(EMAIL_SENDER, RECIPIENT_EMAIL, text)
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
        logger.info(f"获取URL中")
        
        # 使用Jina AI读取网页内容
        result = read_webpage_with_jina(url)
        
        if not result or "data" not in result or "content" not in result["data"]:
            logger.error("无法获取网页内容")
            return
        
        content = result["data"]["content"]
        logger.info(f"成功获取内容，长度: {len(content)} 字符")
        
        # 总结内容 - 添加重试失败处理
        summary = None
        try:
            summary = summarize_with_gemini(content)
            logger.info(f"成功生成摘要，长度: {len(summary)} 字符")
        except Exception as e:
            import traceback
            error_str = str(e)
            
            # 如果是重试失败，发送最终错误通知
            if "RetryError" in error_str or "已重试3次仍失败" in error_str:
                log_details = f"Gemini API重试3次后仍然失败\n模型: gemini-2.5-flash-preview-05-20\nAPI密钥: {GEMINI_API_KEY[:10]}...****\n内容长度: {len(content)} 字符\n完整错误: {traceback.format_exc()}"
                send_error_notification("重试失败", "Gemini API摘要生成重试3次后仍然失败", "Gemini AI", log_info=log_details)
            
            logger.error(f"生成摘要失败，将跳过摘要步骤: {error_str}")
            summary = "由于Gemini API不稳定，无法生成摘要。请稍后重试。"
        
        # 保存到Notion
        page_id = save_to_notion(title, content, summary)
        if page_id:
            logger.info(f"成功保存到Notion！")
        else:
            logger.warning("保存到Notion失败")
        
        # 发送邮件 - 添加重试失败处理
        email_sent = False
        try:
            email_sent = send_email(title, summary, content)
            if email_sent:
                logger.info("成功发送邮件")
            else:
                logger.warning("发送邮件失败")
        except Exception as e:
            import traceback
            error_str = str(e)
            
            # 如果邮件发送时HTML生成失败，也进行处理
            if "生成HTML笔记失败" in error_str:
                log_details = f"HTML笔记生成重试失败\n模型: gemini-2.5-flash-preview-05-20\n完整错误: {traceback.format_exc()}"
                send_error_notification("HTML笔记生成失败", "邮件中的HTML笔记生成失败", "Gemini AI", log_info=log_details)
            
            logger.error(f"发送邮件过程中出错: {error_str}")
            
    except Exception as e:
        import traceback
        logger.error(f"处理过程中发生错误: {str(e)}")
        
        # 发送总体错误通知
        error_msg = f"新闻联播程序运行失败: {str(e)}"
        log_details = f"完整错误堆栈: {traceback.format_exc()}\n\n环境变量状态:\n- JINA_API_KEY: {'已设置' if JINA_API_KEY else '未设置'}\n- GEMINI_API_KEY: {'已设置' if GEMINI_API_KEY else '未设置'}\n- NOTION_API_KEY: {'已设置' if NOTION_API_KEY else '未设置'}\n- EMAIL配置: {'已设置' if EMAIL_ADDRESS and EMAIL_PASSWORD else '未设置'}"
        send_error_notification("程序运行错误", error_msg, "新闻联播自动化系统", log_info=log_details)
        
    finally:
        logger.info("处理完成")

if __name__ == "__main__":
    logger.info("开始运行新闻联播摘要生成程序")
    main()
