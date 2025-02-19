import os
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType

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
    针对 GitHub Actions 环境进行特殊配置
    """
    options = Options()
    
    # 基本配置
    options.add_argument('--headless=new')  # 使用新版本的 headless 模式
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    
    # 额外的稳定性配置
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--window-size=1920,1080')
    
    # 内存相关配置
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-browser-side-navigation')
    
    # User-Agent 设置
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36")
    
    # 在 GitHub Actions 环境中指定 Chrome 路径
    if os.getenv('GITHUB_ACTIONS'):
        options.binary_location = '/usr/bin/google-chrome'
    
    try:
        # 使用 ChromeDriverManager 自动安装和管理 ChromeDriver
        service = Service(ChromeDriverManager(chrome_type=ChromeType.GOOGLE).install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        print(f"Chrome driver initialization failed: {str(e)}")
        raise

def wait_for_elements(driver, selector, timeout=10):
    """
    等待元素加载完成
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
        )
    except Exception as e:
        print(f"等待元素超时: {str(e)}")
        return []

def crawl_page(url, driver):
    """使用 Selenium 爬取单个页面的源码"""
    for attempt in range(MAX_RETRIES):
        try:
            driver.get(url)
            # 使用显式等待替代隐式等待
            wait_for_elements(driver, "div.gallery")
            
            # 检查页面标题是否包含 "404"
            if "404" in driver.title:
                print(f"页面返回 404 错误: {url}")
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
            print(f"爬取页面失败，停止爬取: {url}")
            break

        soup = BeautifulSoup(html, 'html.parser')
        comics = soup.find_all('div', class_='gallery')
        
        if not comics:
            print(f"未找到漫画数据，可能是最后一页: {url}")
            break
        
        # 解析页面中的漫画数据
        for comic in comics:
            try:
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
                    "page": page,
                    "crawled_at": datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"解析漫画数据失败: {str(e)}")
                continue
        
        # 检查是否存在下一页按钮
        next_button = soup.find('a', class_='next')
        if not next_button:
            print(f"已到达最后一页: {url}")
            break
        
        page += 1
        time.sleep(DELAY_SECONDS)
    
    return all_data

def save_to_json(data, period='today', language='chinese'):
    """保存数据到 JSON 文件"""
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"output/{language}-comics-{period}-{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到文件: {filename}")
        return filename
    except Exception as e:
        print(f"保存数据到文件失败: {str(e)}")
        return None

def main():
    """主函数"""
    print(f"开始爬虫任务 - {datetime.now().isoformat()}")
    
    # 初始化 Selenium 驱动
    try:
        driver = setup_driver()
    except Exception as e:
        print(f"初始化 Chrome 驱动失败: {str(e)}")
        return
    
    try:
        # 遍历所有语言进行数据爬取
        for lang, lang_name in LANGUAGES.items():
            print(f"\n开始爬取 {lang_name} 漫画数据...")
            
            # 爬取每日热门数据
            daily_comics = crawl_all_pages('today', lang, driver)
            if daily_comics:
                daily_output = save_to_json(daily_comics, 'today', lang)
                print(f"{lang_name} 每日热门：共爬取 {len(daily_comics)} 条数据，保存至 {daily_output}")
            
            # 爬取每周热门数据
            weekly_comics = crawl_all_pages('week', lang, driver)
            if weekly_comics:
                weekly_output = save_to_json(weekly_comics, 'week', lang)
                print(f"{lang_name} 每周热门：共爬取 {len(weekly_comics)} 条数据，保存至 {weekly_output}")
    
    except Exception as e:
        print(f"爬虫过程中发生错误: {str(e)}")
    
    finally:
        try:
            driver.quit()
        except Exception as e:
            print(f"关闭 Chrome 驱动失败: {str(e)}")
    
    print(f"爬虫任务完成 - {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
