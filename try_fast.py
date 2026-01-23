import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from threading import Lock

# ---------------- CONFIG ----------------
URL = "https://github.com/sayantanmandal1"
ITERATIONS = 1000
NUM_BROWSERS = 5  # Run 5 browsers in parallel
# ----------------------------------------

print_lock = Lock()
counter = 0
counter_lock = Lock()

def get_chrome_options():
    """Get optimized Chrome options"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Faster loading
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--disable-javascript")  # Even faster if JS not needed
    chrome_options.add_argument(f"--remote-debugging-port={9222 + random.randint(0, 100)}")
    return chrome_options

def worker(worker_id, iterations_per_worker):
    """Each worker runs its own browser instance"""
    global counter
    
    driver = None
    try:
        driver = webdriver.Chrome(options=get_chrome_options())
        
        for i in range(iterations_per_worker):
            driver.get(URL)
            time.sleep(0.3)  # Minimal delay
            
            with counter_lock:
                counter += 1
                current = counter
            
            if current % 50 == 0:
                with print_lock:
                    print(f"[Worker {worker_id}] Progress: {current}/{ITERATIONS} ({current/ITERATIONS*100:.1f}%)")
        
        return f"Worker {worker_id} completed {iterations_per_worker} visits"
        
    except Exception as e:
        return f"Worker {worker_id} error: {e}"
    finally:
        if driver:
            driver.quit()

def main():
    start_time = time.time()
    
    print(f"🚀 Starting {NUM_BROWSERS} parallel browsers for {ITERATIONS} total visits...")
    print(f"Each browser will handle ~{ITERATIONS // NUM_BROWSERS} visits\n")
    
    iterations_per_worker = ITERATIONS // NUM_BROWSERS
    remainder = ITERATIONS % NUM_BROWSERS
    
    with ThreadPoolExecutor(max_workers=NUM_BROWSERS) as executor:
        futures = []
        for i in range(NUM_BROWSERS):
            # Distribute remainder among first workers
            iters = iterations_per_worker + (1 if i < remainder else 0)
            futures.append(executor.submit(worker, i + 1, iters))
        
        # Wait for all to complete
        for future in as_completed(futures):
            result = future.result()
            print(result)
    
    elapsed = time.time() - start_time
    print(f"\n✅ Completed {ITERATIONS} visits in {elapsed:.1f} seconds")
    print(f"⚡ Average: {elapsed/ITERATIONS:.2f} seconds per visit")
    print(f"🔥 Speed: {ITERATIONS/elapsed:.1f} visits per second")

if __name__ == "__main__":
    main()
