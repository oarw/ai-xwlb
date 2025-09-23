import logging
import smtplib
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import config as cfg
from .gemini_client import generate_html_notes

logger = logging.getLogger(__name__)


def send_email(title: str, summary: str, content: Optional[str] = None) -> bool:
    msg = MIMEMultipart("alternative")
    msg["From"] = cfg.EMAIL_SENDER
    msg["To"] = cfg.RECIPIENT_EMAIL
    msg["Subject"] = f"【新闻联播学习笔记】{title}"

    html_notes = generate_html_notes(content or summary, title)
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

    text_content = f"""
    {title} - 学习笔记

    {summary}

    ------
    此邮件由自动化系统发送，请勿回复。
    """

    part1 = MIMEText(text_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    try:
        logger.info("正在发送邮件....")
        server = smtplib.SMTP(cfg.SMTP_SERVER, cfg.SMTP_PORT)
        server.starttls()
        server.login(cfg.EMAIL_ADDRESS, cfg.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(cfg.EMAIL_SENDER, cfg.RECIPIENT_EMAIL, text)
        server.quit()
        logger.info("HTML邮件发送成功")
        return True
    except Exception as e:
        logger.error(f"发送邮件失败: {str(e)}")
        return False


