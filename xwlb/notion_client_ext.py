import datetime
import logging
from notion_client import Client

from . import config as cfg

logger = logging.getLogger(__name__)


def get_notion_database_properties():
    try:
        notion = Client(auth=cfg.NOTION_API_KEY)
        database = notion.databases.retrieve(database_id=cfg.NOTION_DATABASE_ID)
        logger.info("已获取Notion数据库属性")
        return database["properties"]
    except Exception as e:
        logger.error(f"获取Notion数据库属性失败: {str(e)}")
        return None


def save_to_notion(title: str, content: str, summary: str):
    notion = Client(auth=cfg.NOTION_API_KEY)

    db_properties = get_notion_database_properties()
    if not db_properties:
        logger.error("无法获取Notion数据库属性，保存失败")
        return None

    title_property_name = None
    date_property_name = None
    for name, prop in db_properties.items():
        if prop["type"] == "title":
            title_property_name = name
        elif prop["type"] == "date":
            date_property_name = name
    if not title_property_name or not date_property_name:
        logger.error(
            f"未找到所需属性，标题属性: {title_property_name}, 日期属性: {date_property_name}"
        )
        return None

    def chunk_text(text: str, max_length: int = 2000):
        return [text[i : i + max_length] for i in range(0, len(text), max_length)]

    content_chunks = chunk_text(content)
    summary_chunks = chunk_text(summary)

    children = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "摘要"}}]
            },
        }
    ]
    for chunk in summary_chunks:
        children.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
            }
        )
    children.append(
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"type": "text", "text": {"content": "原文"}}]},
        }
    )
    for chunk in content_chunks:
        children.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
            }
        )

    properties = {
        title_property_name: {"title": [{"text": {"content": title}}]},
        date_property_name: {"date": {"start": datetime.datetime.now().strftime("%Y-%m-%d")}},
    }

    try:
        logger.info("正在保存到Notion")
        page = notion.pages.create(
            parent={"database_id": cfg.NOTION_DATABASE_ID},
            properties=properties,
            children=children,
        )
        return page["id"]
    except Exception as e:
        logger.error(f"保存到Notion失败: {str(e)}")
        return None


