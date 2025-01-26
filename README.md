# NHentai 漫画数据采集

自动采集 nhentai 网站上的热门漫画数据，支持多语言和不同时间维度的数据统计。

## 功能特点

- 支持多语言
  - 中文漫画
  - 日文漫画
  - 英文漫画

- 数据维度
  - 每日热门排行
  - 每周热门排行

- 自动化部署
  - 每日自动运行
  - GitHub Actions 自动发布
  - 自动生成 Release

## 数据格式

采集的数据以 JSON 格式保存，包含以下字段：
```json
{
  "title": "标题",
  "link": "链接地址",
  "cover": "封面图片地址",
  "page": "来源页码"
}
```

## 自动发布

- 每天 23:00 UTC 自动运行
- 在 GitHub Releases 中发布数据
- 文件命名格式：`{language}-comics-{period}-{date}.json`
  - language: chinese/japanese/english
  - period: today/week
  - date: YYYY-MM-DD

## 手动运行

1. 安装依赖
```bash
pip install -r src/requirements.txt
```

2. 运行爬虫
```bash
python src/crawler.py
```

## 数据文件

每次运行会生成 6 个数据文件：
- chinese-comics-today-{date}.json
- chinese-comics-week-{date}.json
- japanese-comics-today-{date}.json
- japanese-comics-week-{date}.json
- english-comics-today-{date}.json
- english-comics-week-{date}.json

## 注意事项

- 请遵守目标网站的爬虫规则
- 建议适当设置爬取延迟，避免对服务器造成压力
- 数据仅供学习研究使用


