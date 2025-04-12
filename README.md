# 新闻联播自动摘要工具
测试
这个工具可以自动获取前一天的新闻联播文字稿，生成摘要，特别关注与考研考公相关的内容，并将结果保存到Notion和通过邮件发送。

## 功能

- 自动获取前一天的新闻联播文字稿URL
- 使用Jina AI的Reader API读取网页内容
- 使用OpenAI API生成摘要，重点关注考研考公相关内容
- 将原文和摘要保存到Notion数据库
- 通过邮件发送摘要

## 环境变量设置

在运行程序前，请设置以下环境变量：

```
JINA_API_KEY=your_jina_api_key
OPENAI_API_KEY=your_openai_api_key
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
EMAIL_ADDRESS=your_email_address
EMAIL_PASSWORD=your_email_password
RECIPIENT_EMAIL=recipient_email_address
```

## 安装和使用

1. 安装依赖：
```
pip install -r requirements.txt
```

2. 设置环境变量（可以使用.env文件）

3. 运行程序：
```
python xwlb_daily.py
```

## Notion数据库设置

创建一个包含以下属性的Notion数据库：
- 标题（title类型）
- 日期（date类型）

免费获取您的 Jina AI API 密钥：https://jina.ai/?sui=apikey
