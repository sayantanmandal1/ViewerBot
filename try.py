import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# ---------------- CONFIG ----------------
URL = "https://github.com/sayantanmandal1"   # 🔁 PUT YOUR WEBSITE LINK HERE
ITERATIONS = 1000
MIN_DELAY = 1
MAX_DELAY = 5

# Path to your existing Chrome profile (Windows)
CHROME_PROFILE_PATH = r"C:\Users\msaya\AppData\Local\Google\Chrome\User Data"
PROFILE_NAME = "Default"  # or "Profile 1", "Profile 2", etc.
# ----------------------------------------

chrome_options = Options()

# Run headless (new headless is more stable)
chrome_options.add_argument("--headless=new")

# Use existing browser profile - but create a copy to avoid conflicts
chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}\\Selenium")
chrome_options.add_argument(f"--profile-directory={PROFILE_NAME}")

# Performance & stability flags
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-plugins")
chrome_options.add_argument("--disable-images")
chrome_options.add_argument("--disable-javascript")
chrome_options.add_argument("--remote-debugging-port=9222")

# Create driver
try:
    driver = webdriver.Chrome(options=chrome_options)
except Exception as e:
    print(f"Failed to create Chrome driver: {e}")
    print("Trying with minimal options...")
    
    # Fallback with minimal options
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9223")
    
    driver = webdriver.Chrome(options=chrome_options)

try:
    for i in range(ITERATIONS):
        driver.get(URL)

        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        print(f"[{i+1}/{ITERATIONS}] Opened → sleeping for {delay:.2f}s")

        time.sleep(delay)

finally:
    driver.quit()
    print("✅ Finished all iterations and closed browser.")
