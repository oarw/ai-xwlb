import os
from dotenv import load_dotenv


# 加载环境变量（允许 .env）
load_dotenv()

# API 与服务配置
JINA_API_KEY = os.environ.get("JINA_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 邮件配置
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.mailersend.net")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))


REQUIRED_VARS = [
    "JINA_API_KEY",
    "GEMINI_API_KEY",
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
    "EMAIL_ADDRESS",
    "EMAIL_PASSWORD",
    "RECIPIENT_EMAIL",
]


def get_missing_vars():
    return [var for var in REQUIRED_VARS if not os.environ.get(var)]


