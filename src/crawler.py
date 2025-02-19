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

# Constants
MAX_RETRIES = 3
DELAY_SECONDS = 1
BASE_DOMAIN = "nhentai.net"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
MAX_ITEMS = 200

LANGUAGES = {
    'chinese': '中文',
    'japanese': '日文',
    'english': '英文'
}


def get_current_time():
    """获取当前 UTC 时间"""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def setup_chrome_options():
    """配置 Chrome 选项"""
    options = Options()
    # options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-browser-side-navigation')
    options.add_argument(f'--user-agent={USER_AGENT}')

    if os.getenv('GITHUB_ACTIONS'):
        options.binary_location = '/usr/bin/google-chrome'
        options.add_argument('--remote-debugging-port=9222')

    return options


def setup_driver():
    """设置和初始化 WebDriver"""
    print(f"[{get_current_time()}] 正在初始化 Chrome WebDriver...")
    try:
        options = setup_chrome_options()
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print(f"[{get_current_time()}] Chrome WebDriver 初始化成功")
        return driver
    except Exception as e:
        print(f"[{get_current_time()}] Chrome WebDriver 初始化失败: {str(e)}")
        raise


def wait_for_elements(driver, selector, timeout=10):
    """等待元素加载完成"""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
        )
    except Exception as e:
        print(f"[{get_current_time()}] 等待元素超时: {str(e)}")
        return []


def crawl_page(url, driver):
    """爬取单个页面内容"""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"[{get_current_time()}] 正在请求页面: {url}")
            driver.get(url)
            galleries = wait_for_elements(driver, "div.gallery")
            if not galleries:
                print(f"[{get_current_time()}] 页面未找到内容: {url}")
                return None
            if "404" in driver.title:
                print(f"[{get_current_time()}] 页面返回 404: {url}")
                return None
            return driver.page_source
        except Exception as e:
            print(f"[{get_current_time()}] 请求失败 ({attempt + 1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(5)
    return None


def get_comic_details(comic_url, driver):
    """
    进入漫画详情页，提取详细信息：
      - pages: 漫画页数
      - uploaded_at: 上传时间（<time> 标签的 datetime 属性）
      - tags: 剩余标签信息，按分类存放（例如 Parodies、Tags、Artists、Languages、Categories 等）
    """
    details = {"pages": None, "uploaded_at": "", "tags": {}}
    try:
        print(f"[{get_current_time()}] 正在请求漫画详情页面: {comic_url}")
        driver.get(comic_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "section#tags"))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        section = soup.find("section", id="tags")
        if not section:
            print(f"[{get_current_time()}] 未找到标签区域: {comic_url}")
            return details

        tag_containers = section.find_all("div", class_="tag-container")
        for container in tag_containers:
            # 获取标签分类名称，通常在第一个文本节点中
            category = ""
            if container.contents:
                first = container.contents[0]
                if isinstance(first, str):
                    category = first.strip().strip(":")
            if not category:
                continue

            # 针对不同分类做处理
            if category.lower() == "pages":
                a_tag = container.find("a", class_="tag")
                if a_tag:
                    span_name = a_tag.find("span", class_="name")
                    if span_name:
                        try:
                            details["pages"] = int(span_name.text.strip())
                        except ValueError:
                            details["pages"] = span_name.text.strip()
            elif category.lower() == "uploaded":
                time_tag = container.find("time")
                if time_tag and time_tag.has_attr("datetime"):
                    details["uploaded_at"] = time_tag["datetime"]
            else:
                # 其他分类归纳到 tags 中
                tags_list = []
                span_tags = container.find("span", class_="tags")
                if span_tags:
                    a_tags = span_tags.find_all("a", class_="tag")
                    for a in a_tags:
                        tag_name = a.find("span", class_="name").text.strip() if a.find("span", class_="name") else ""
                        tag_count = a.find("span", class_="count").text.strip() if a.find("span", class_="count") else ""
                        tag_link = a.get("href", "")
                        tags_list.append({
                            "name": tag_name,
                            "count": tag_count,
                            "link": f"https://{BASE_DOMAIN}{tag_link}" if tag_link else ""
                        })
                details["tags"][category] = tags_list

        return details
    except Exception as e:
        print(f"[{get_current_time()}] 获取漫画详情失败: {comic_url}, 错误: {str(e)}")
        return details


def parse_comic_data(comic, driver):
    """解析列表页中漫画数据，并进入详情页获取详细信息"""
    try:
        caption_div = comic.find('div', class_='caption')
        link_tag = comic.find('a')
        img_tag = comic.find('img')
        comic_link = f"https://{BASE_DOMAIN}{link_tag['href']}" if link_tag and link_tag.get('href') else ""
        # 获取漫画详情：页数、上传时间以及其他标签信息
        comic_details = get_comic_details(comic_link, driver) if comic_link else {}
        return {
            "title": caption_div.text.strip() if caption_div else "未知标题",
            "link": comic_link,
            "cover": img_tag['data-src'] if img_tag and img_tag.get('data-src') else "",
            "page": None,  # 后续在爬取页数时赋值
            "uploaded_at": comic_details.get("uploaded_at", ""),
            "pages": comic_details.get("pages", ""),
            "tags": comic_details.get("tags", {}),
            "crawled_at": get_current_time()
        }
    except Exception as e:
        print(f"[{get_current_time()}] 解析漫画数据失败: {str(e)}")
        return None


def crawl_all_pages(period='today', language='chinese', driver=None, limit=MAX_ITEMS):
    """爬取所有分页数据，最多获取前 limit 条数据"""
    base_url = f"https://{BASE_DOMAIN}/language/{language}/popular-{period}"
    page = 1
    all_data = []

    while True:
        url = f"{base_url}?page={page}"
        print(f"[{get_current_time()}] 正在爬取 {LANGUAGES.get(language, language)}语 {period} 排行第 {page} 页")
        html = crawl_page(url, driver)
        if not html:
            break

        soup = BeautifulSoup(html, 'html.parser')
        comics = soup.find_all('div', class_='gallery')
        if not comics:
            print(f"[{get_current_time()}] 未找到更多数据，结束爬取")
            break

        for comic in comics:
            if len(all_data) >= limit:
                break
            comic_data = parse_comic_data(comic, driver)
            if comic_data:
                comic_data['page'] = page
                all_data.append(comic_data)

        print(f"[{get_current_time()}] 成功解析第 {page} 页，当前总数: {len(all_data)} 条数据")
        if len(all_data) >= limit:
            print(f"[{get_current_time()}] 已获取到前 {limit} 条数据，停止爬取")
            break

        next_button = soup.find('a', class_='next')
        if not next_button:
            print(f"[{get_current_time()}] 已到达最后一页")
            break

        page += 1
        time.sleep(DELAY_SECONDS)

    return all_data[:limit]


def save_to_json(data, period='today', language='chinese'):
    """保存数据到 JSON 文件"""
    if not data:
        print(f"[{get_current_time()}] 没有数据需要保存")
        return None
    try:
        os.makedirs("output", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d")
        filename = f"output/{language}-comics-{period}-{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "language": language,
                    "period": period,
                    "timestamp": get_current_time(),
                    "total_items": len(data)
                },
                "data": data
            }, f, ensure_ascii=False, indent=2)
        print(f"[{get_current_time()}] 数据已保存到: {filename}")
        return filename
    except Exception as e:
        print(f"[{get_current_time()}] 保存数据失败: {str(e)}")
        return None


def main():
    """主函数"""
    start_time = get_current_time()
    print(f"[{start_time}] 开始爬虫任务")
    try:
        driver = setup_driver()
    except Exception as e:
        print(f"[{get_current_time()}] 初始化失败，任务终止: {str(e)}")
        return

    try:
        for lang, lang_name in LANGUAGES.items():
            print(f"\n[{get_current_time()}] 开始爬取 {lang_name} 数据")
            print(f"\n[{get_current_time()}] 爬取 {lang_name} 每日热门...")
            daily_comics = crawl_all_pages('today', lang, driver)
            if daily_comics:
                save_to_json(daily_comics, 'today', lang)
                print(f"[{get_current_time()}] {lang_name} 每日热门：{len(daily_comics)} 条数据")

            print(f"\n[{get_current_time()}] 爬取 {lang_name} 每周热门...")
            weekly_comics = crawl_all_pages('week', lang, driver)
            if weekly_comics:
                save_to_json(weekly_comics, 'week', lang)
                print(f"[{get_current_time()}] {lang_name} 每周热门：{len(weekly_comics)} 条数据")
    except Exception as e:
        print(f"[{get_current_time()}] 爬虫过程发生错误: {str(e)}")
    finally:
        try:
            driver.quit()
            print(f"[{get_current_time()}] 已关闭 Chrome WebDriver")
        except Exception as e:
            print(f"[{get_current_time()}] 关闭 WebDriver 时发生错误: {str(e)}")

    end_time = get_current_time()
    print(f"[{end_time}] 爬虫任务完成")


if __name__ == "__main__":
    main()
