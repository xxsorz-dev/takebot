import time
import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import os

# ====================== 配置 ======================
SELLER_EMAIL = "xrkdzsw@163.com"
SELLER_PWD = "Aa040406@"
MY_STORE_NAME = "High-quality good things"
START_HOUR = 10
STOP_HOUR = 9

# 云端路径
EXCEL_PATH = "products.xlsx"

# ====================== 读取商品 ======================
def load_products_from_excel():
    df = pd.read_excel(EXCEL_PATH, dtype={"min_price": float, "enabled": int})
    products = []
    for _, row in df.iterrows():
        url = str(row["url"]).strip()
        min_price = float(row["min_price"])
        enabled = int(row["enabled"]) == 1
        products.append({
            "url": url,
            "min_price": min_price,
            "enabled": enabled
        })
    return products

last_prices = {}

# ====================== 运行时间判断 ======================
def is_running_time():
    now = datetime.datetime.now()
    current_hour = now.hour
    if START_HOUR > STOP_HOUR:
        return current_hour >= START_HOUR or current_hour < STOP_HOUR
    else:
        return STOP_HOUR <= current_hour < START_HOUR

# ====================== 清洗价格 ======================
def clean_price(price_text):
    return float(price_text.replace("R", "").replace(" ", "").replace(",", ""))

# ====================== 抓取用：无头浏览器（云端可用） ======================
def get_headless_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(20)
    driver.implicitly_wait(2)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ====================== 改价用：云端正常浏览器（Render支持） ======================
def get_normal_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(20)
    driver.implicitly_wait(2)
    return driver

# ====================== 单次抓取 ======================
def get_single_product_info(driver, url, min_price):
    driver.get(url)
    title = WebDriverWait(driver, 8).until(
        EC.presence_of_element_located((By.TAG_NAME, "h1"))
    ).text.strip()
    p1_text = "0"
    try:
        price_elem = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "div[data-ref='price'] span.currency.whitespace-nowrap.plus:first-child"
            ))
        )
        p1_text = price_elem.text.strip()
    except (TimeoutException, NoSuchElementException):
        all_prices = driver.find_elements(
            By.CSS_SELECTOR,
            "div[data-ref='price'] span.currency.whitespace-nowrap.plus"
        )
        if all_prices:
            p1_text = all_prices[0].text.strip()
    p1 = clean_price(p1_text)
    is_my_store = False
    try:
        seller_elem = driver.find_element(By.CSS_SELECTOR, "a[href*='seller']")
        seller_name = seller_elem.text.strip()
        if MY_STORE_NAME in seller_name:
            is_my_store = True
    except:
        pass
    if is_my_store:
        target_price = p1
    else:
        target_price = p1 - 1
    below_limit = target_price < min_price
    if below_limit:
        target_price = min_price
    return {
        "title": title,
        "url": url,
        "market_price": p1,
        "my_price": target_price,
        "is_my_store": is_my_store,
        "below_limit": below_limit,
        "min_price": min_price,
        "enabled": True
    }

# ====================== 批量抓取 ======================
def get_batch_products_info():
    products = load_products_from_excel()
    result = []
    driver = get_headless_driver()
    for item in products:
        url = item["url"]
        min_price = item["min_price"]
        enabled = item["enabled"]
        if not enabled:
            print(f"⏹️ 监控已关闭：{url} → 跳过")
            continue
        ok = False
        for retry in range(2):
            try:
                info = get_single_product_info(driver, url, min_price)
                result.append(info)
                print(f"📊 售价: {info['market_price']}")
                if info["below_limit"]:
                    print(f"⏭️ {info['title']} | 已触发保护价 {min_price}")
                elif info["is_my_store"]:
                    print(f"✅ {info['title']} | 已是自己店铺，跳过")
                else:
                    print(f"🔄 {info['title']} | 新价格: {info['my_price']}")
                ok = True
                break
            except Exception as e:
                if retry == 0:
                    print(f"⚠️ 抓取重试一次：{url}")
                    time.sleep(1)
                else:
                    print(f"❌ 抓取最终失败：{url}")
        if not ok:
            continue
    driver.quit()
    return result

# ====================== 批量改价 ======================
def batch_update_prices(products):
    driver = get_normal_driver()
    try:
        driver.get("https://sellers.takealot.com/login")
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.ID, "email")))
        driver.find_element(By.ID, "email").send_keys(SELLER_EMAIL)
        driver.find_element(By.ID, "password").send_keys(SELLER_PWD)
        driver.find_element(By.XPATH, '//button[@type="submit"]').click()
        time.sleep(5)
        driver.get("https://sellers.takealot.com/existing-offers/manage-offers?m=default")
        time.sleep(3)
        for p in products:
            if not p["enabled"] or p["is_my_store"] or p["below_limit"]:
                continue
            try:
                print(f"\n🔄 改价：{p['title']}")
                search_box = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//input[@placeholder='Search...' and contains(@class,'chakra-input')]"
                    ))
                )
                search_box.clear()
                search_box.send_keys(p["title"])
                time.sleep(2)
                price_input = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable((
                        By.CSS_SELECTOR,
                        "input[name='Selling Price'].chakra-numberinput__field"
                    ))
                )
                price_input.click()
                time.sleep(0.2)
                price_input.send_keys(Keys.CONTROL, "a")
                price_input.send_keys(Keys.BACKSPACE)
                price_input.send_keys(str(int(p["my_price"])))
                time.sleep(0.5)
                driver.find_element(By.TAG_NAME, "body").click()
                search_box.clear()
                time.sleep(0.5)
                last_prices[p["url"]] = p["my_price"]
            except Exception as e:
                print(f"❌ 改价失败：{p['title']}")
                driver.refresh()
                time.sleep(3)
    finally:
        driver.quit()
        print("\n✅ 批量改价完成！")

# ====================== 主程序 ======================
print("=== 云端24小时跟价机器人 ===")
print(f"⏰ 运行时间：{START_HOUR}:00 - 次日{STOP_HOUR}:00")
while True:
    now = datetime.datetime.now()
    print(f"\n=====================================")
    print(f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")
    if is_running_time():
        print("✅ 开始无头静默监控抓取...")
        products = get_batch_products_info()
        need_update = any(
            p["enabled"] and not p["is_my_store"] and not p["below_limit"]
            for p in products
        )
        if need_update:
            print("\n📌 云端浏览器自动改价...")
            batch_update_prices(products)
        else:
            print("\n✅ 全部已是最优价！")
        print("\n等待 60 秒...")
        time.sleep(60)
    else:
        print("😴 非运行时间，休眠5分钟")
        time.sleep(300)