import time
import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

SELLER_EMAIL = "xrkdzsw@163.com"
SELLER_PWD = "Aa040406@"
MY_STORE_NAME = "High-quality good things"
START_HOUR = 10
STOP_HOUR = 9
EXCEL_PATH = "products.xlsx"

def load_products_from_excel():
    df = pd.read_excel(EXCEL_PATH, dtype={"min_price": float, "enabled": int})
    products = []
    for _, row in df.iterrows():
        url = str(row["url"]).strip()
        min_price = float(row["min_price"])
        enabled = int(row["enabled"]) == 1
        products.append({"url":url,"min_price":min_price,"enabled":enabled})
    return products

def is_running_time():
    now = datetime.datetime.now()
    h = now.hour
    return h >= START_HOUR or h < STOP_HOUR

def clean_price(t):
    return float(t.replace("R","").replace(" ","").replace(",",""))

def get_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--single-process")
    return webdriver.Chrome(options=opts)

def get_product_info(url, min_p):
    driver = get_driver()
    driver.get(url)
    time.sleep(2)
    title = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.TAG_NAME,"h1"))).text.strip()
    price_text = WebDriverWait(driver,8).until(EC.presence_of_element_located((By.CSS_SELECTOR,"div[data-ref='price'] span"))).text.strip()
    driver.quit()
    p = clean_price(price_text)
    target = p - 1
    if target < min_p:
        target = min_p
    return {"title":title,"price":p,"suggest":target}

def main_loop():
    print("✅ 机器人已启动，前台常驻运行")
    while True:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n==== {now} ====")
        if is_running_time():
            print("开始抓取商品...")
            goods = load_products_from_excel()
            for g in goods:
                try:
                    info = get_product_info(g["url"], g["min_price"])
                    print(f"{info['title']} | 市价:{info['price']} 建议:{info['suggest']}")
                except Exception as e:
                    print("抓取失败:",e)
                time.sleep(3)
        else:
            print("非运行时段，休眠中")
        time.sleep(60)

if __name__ == "__main__":
    main_loop()
