import datetime
import urllib.parse


def get_yesterday_url():
    """获取前一天的新闻联播 URL 和标题。"""
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    year = yesterday.strftime("%Y")
    month = yesterday.strftime("%m")
    day = yesterday.strftime("%d")

    date_part = f"{year}年{month}月{day}日新闻联播文字版"
    encoded_date = urllib.parse.quote(date_part)

    url = f"http://mrxwlb.com/{year}/{month}/{day}/{encoded_date}/"
    title = f"{year}年{month}月{day}日新闻联播"
    return url, title


