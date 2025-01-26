import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime

# 配置参数
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
MAX_RETRIES = 3
DELAY_SECONDS = 0.5

# 支持的语言配置
LANGUAGES = {
    'chinese': '中文',
    'japanese': '日文',
    'english': '英文'
}

def crawl_page(url):
    """爬取单页数据"""
    for _ in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                return response
            elif response.status_code == 404:  # 无更多页面
                return None
        except Exception as e:
            print(f"请求失败: {e}, 重试中...")
            time.sleep(5)
    return None

def crawl_all_pages(period='today', language='chinese'):
    """自动爬取所有分页
    
    Args:
        period: 时间周期，可选 'today' 或 'week'
        language: 语言，可选 'chinese', 'japanese', 'english'
    """
    base_url = f"https://nhentai.net/language/{language}/popular-{period}"
    page = 1
    all_data = []
    
    while True:
        url = f"{base_url}?page={page}"
        print(f"正在爬取{LANGUAGES.get(language, language)}语{period}排行第 {page} 页: {url}")
        
        response = crawl_page(url)
        if not response:
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        comics = soup.find_all('div', class_='gallery')
        
        # 解析数据
        for comic in comics:
            title = comic.find('div', class_='caption').text.strip()
            link = "https://nhentai.net" + comic.find('a')['href']
            cover = comic.find('img')['data-src']
            all_data.append({
                "title": title,
                "link": link,
                "cover": cover,
                "page": page  # 记录来源页码
            })
        
        # 检查是否存在下一页按钮
        next_button = soup.find('a', class_='next')
        if not next_button:
            break
            
        page += 1
        time.sleep(DELAY_SECONDS)  # 礼貌性延迟
    
    return all_data

def save_to_json(data, period='today', language='chinese'):
    """保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        period: 时间周期，用于文件名
        language: 语言标识
    """
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"output/{language}-comics-{period}-{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename

if __name__ == "__main__":
    # 遍历所有语言
    for lang, lang_name in LANGUAGES.items():
        print(f"\n开始爬取{lang_name}漫画数据...")
        
        # 爬取每日热门
        daily_comics = crawl_all_pages('today', lang)
        daily_output = save_to_json(daily_comics, 'today', lang)
        print(f"{lang_name}每日热门：共爬取 {len(daily_comics)} 条数据，保存至 {daily_output}")
        
        # 爬取每周热门
        weekly_comics = crawl_all_pages('week', lang)
        weekly_output = save_to_json(weekly_comics, 'week', lang)
        print(f"{lang_name}每周热门：共爬取 {len(weekly_comics)} 条数据，保存至 {weekly_output}")