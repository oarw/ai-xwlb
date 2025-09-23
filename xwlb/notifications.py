import datetime
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import config as cfg

logger = logging.getLogger(__name__)


def send_error_notification(error_type, error_message, api_name, log_info=None):
    """发送 API 错误通知邮件。"""
    msg = MIMEMultipart()
    msg["From"] = cfg.EMAIL_SENDER
    msg["To"] = cfg.RECIPIENT_EMAIL
    msg["Subject"] = f"⚠️ 【API错误通知】{api_name} API异常"

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

    part1 = MIMEText(text_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")

    msg.attach(part1)
    msg.attach(part2)

    try:
        logger.info(f"正在发送{api_name} API错误通知邮件...")
        server = smtplib.SMTP(cfg.SMTP_SERVER, cfg.SMTP_PORT)
        server.starttls()
        server.login(cfg.EMAIL_ADDRESS, cfg.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(cfg.EMAIL_SENDER, cfg.RECIPIENT_EMAIL, text)
        server.quit()
        logger.info(f"{api_name} API错误通知邮件发送成功")
        return True
    except Exception as e:
        logger.error(f"发送{api_name} API错误通知邮件失败: {str(e)}")
        return False


