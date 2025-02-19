import os
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 重试次数和延迟设置
MAX_RETRIES = 3
DELAY_SECONDS = 0.5

# 支持的语言配置
LANGUAGES = {
    'chinese': '中文',
    'japanese': '日文',
    'english': '英文'
}

def setup_driver():
    """
    设置 Selenium Chrome 驱动（无头模式），
    使用 webdriver-manager 自动下载与 Chromium 版本匹配的 ChromeDriver
    """
    options = Options()
    options.add_argument('--headless')  # 无头模式，不显示浏览器窗口
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 设置自定义的 User-Agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36")
    # 指定 Chromium 浏览器二进制文件路径（GitHub Actions Ubuntu 环境中已安装 chromium-browser）
    options.binary_location = '/usr/bin/chromium-browser'
    
    # 自动下载与 Chromium 版本匹配的 ChromeDriver
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    return driver

def crawl_page(url, driver):
    """使用 Selenium 爬取单个页面的源码"""
    for attempt in range(MAX_RETRIES):
        try:
            driver.get(url)
            # 等待页面加载完成（这里采用简单等待，可替换为 WebDriverWait）
            time.sleep(3)
            # 检查页面标题是否包含 "404"
            if "404" in driver.title:
                return None
            return driver.page_source
        except Exception as e:
            print(f"请求失败: {e}, 正在重试（{attempt+1}/{MAX_RETRIES}）...")
            time.sleep(5)
    return None

def crawl_all_pages(period='today', language='chinese', driver=None):
    """
    自动爬取所有分页数据

    Args:
        period: 时间周期，可选 'today' 或 'week'
        language: 语言，可选 'chinese', 'japanese', 'english'
        driver: Selenium 驱动实例
    """
    base_url = f"https://nhentai.net/language/{language}/popular-{period}"
    page = 1
    all_data = []
    
    while True:
        url = f"{base_url}?page={page}"
        print(f"正在爬取 {LANGUAGES.get(language, language)}语 {period} 排行第 {page} 页: {url}")
        
        html = crawl_page(url, driver)
        if not html:
            break

        soup = BeautifulSoup(html, 'html.parser')
        comics = soup.find_all('div', class_='gallery')
        if not comics:
            break
        
        # 解析页面中的漫画数据
        for comic in comics:
            caption_div = comic.find('div', class_='caption')
            title = caption_div.text.strip() if caption_div else "未知标题"
            link_tag = comic.find('a')
            link = "https://nhentai.net" + link_tag['href'] if link_tag and link_tag.get('href') else ""
            img_tag = comic.find('img')
            cover = img_tag['data-src'] if img_tag and img_tag.get('data-src') else ""
            all_data.append({
                "title": title,
                "link": link,
                "cover": cover,
                "page": page
            })
        
        # 检查是否存在下一页按钮
        next_button = soup.find('a', class_='next')
        if not next_button:
            break
        
        page += 1
        time.sleep(DELAY_SECONDS)
    
    return all_data

def save_to_json(data, period='today', language='chinese'):
    """保存数据到 JSON 文件"""
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"output/{language}-comics-{period}-{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filename

if __name__ == "__main__":
    # 初始化 Selenium 驱动
    driver = setup_driver()
    
    try:
        # 遍历所有语言进行数据爬取
        for lang, lang_name in LANGUAGES.items():
            print(f"\n开始爬取 {lang_name} 漫画数据...")
            
            # 爬取每日热门数据
            daily_comics = crawl_all_pages('today', lang, driver)
            daily_output = save_to_json(daily_comics, 'today', lang)
            print(f"{lang_name} 每日热门：共爬取 {len(daily_comics)} 条数据，保存至 {daily_output}")
            
            # 爬取每周热门数据
            weekly_comics = crawl_all_pages('week', lang, driver)
            weekly_output = save_to_json(weekly_comics, 'week', lang)
            print(f"{lang_name} 每周热门：共爬取 {len(weekly_comics)} 条数据，保存至 {weekly_output}")
    
    finally:
        driver.quit()
