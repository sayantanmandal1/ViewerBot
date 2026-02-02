import os
import platform
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional
import random

app = FastAPI(title="Viewer Bot API", description="A simple viewer bot for websites", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class BotStartRequest(BaseModel):
    url: str
    iterations: int = 100
    parallel_browsers: int = 3  # New: number of parallel browsers
    
    @validator('url')
    def validate_url(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('URL is required')
        if not v.startswith(('http://', 'https://')):
            v = 'https://' + v
        return v
    
    @validator('iterations')
    def validate_iterations(cls, v):
        if v <= 0 or v > 10000:
            raise ValueError('Iterations must be between 1 and 10000')
        return v
    
    @validator('parallel_browsers')
    def validate_parallel_browsers(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Parallel browsers must be between 1 and 10')
        return v

class BotStartResponse(BaseModel):
    taskId: str
    message: str
    url: str
    iterations: int
    parallel_browsers: int

class TaskStatus(BaseModel):
    status: str
    current: int
    total: int
    message: str

class HealthResponse(BaseModel):
    status: str
    message: str

# Global variable to track running tasks
running_tasks = {}
active_drivers = {}  # Track active driver instances for cleanup
task_stop_flags = {}  # Track stop flags for each task

class ViewerBot:
    def __init__(self, url, iterations, parallel_browsers=3):
        self.url = url
        self.iterations = iterations
        self.parallel_browsers = parallel_browsers
        self.is_running = False
        self.current_iteration = 0
        self.counter_lock = threading.Lock()
        
    def get_chrome_options(self, worker_id=0):
        """Get Chrome options based on environment"""
        chrome_options = Options()
        
        # Detect if running in Docker
        is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)
        is_windows = platform.system() == 'Windows'
        
        # Basic headless setup
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Performance optimizations
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-images")  # Faster loading
        chrome_options.add_argument("--blink-settings=imagesEnabled=false")
        
        # Set user data directory based on environment with unique port per worker
        if is_docker:
            chrome_options.add_argument(f"--user-data-dir=/app/chrome-data-{worker_id}")
            chrome_options.add_argument(f"--remote-debugging-port={9222 + worker_id}")
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        elif is_windows:
            import tempfile
            temp_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            chrome_options.add_argument(f"--remote-debugging-port={9222 + worker_id}")
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebDriver/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        else:
            chrome_options.add_argument(f"--user-data-dir=/tmp/chrome-data-{worker_id}")
            chrome_options.add_argument(f"--remote-debugging-port={9222 + worker_id}")
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        chrome_options.add_argument(f"--user-agent={user_agent}")
        chrome_options.add_argument("--profile-directory=Default")
        
        # Prefs for a more realistic browser
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
                "media_stream": 2,
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Anti-detection measures
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        return chrome_options
        
    def worker(self, worker_id, iterations_per_worker, task_id):
        """Each worker runs its own browser instance"""
        driver = None
        
        try:
            # Get Chrome options for this worker
            chrome_options = self.get_chrome_options(worker_id)
            
            # Create Chrome driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Store driver reference
            if task_id not in active_drivers:
                active_drivers[task_id] = []
            active_drivers[task_id].append(driver)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            for i in range(iterations_per_worker):
                # Check stop flag
                if task_id in task_stop_flags and task_stop_flags[task_id]:
                    print(f"Worker {worker_id} stopping...")
                    break
                
                # Navigate to URL
                driver.get(self.url)
                
                # Minimal wait for page load
                time.sleep(0.5)
                
                # Optional: Quick scroll every 10th visit
                if i % 10 == 0:
                    try:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                        time.sleep(0.3)
                    except:
                        pass
                
                # Update counter
                with self.counter_lock:
                    self.current_iteration += 1
                    current = self.current_iteration
                
                # Update progress every 10 iterations
                if current % 10 == 0 or current == self.iterations:
                    running_tasks[task_id] = {
                        'status': 'running',
                        'current': current,
                        'total': self.iterations,
                        'message': f'Visit {current}/{self.iterations}'
                    }
            
            return f"Worker {worker_id} completed"
            
        except Exception as e:
            print(f"Worker {worker_id} error: {e}")
            return f"Worker {worker_id} error: {str(e)}"
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def run(self, task_id):
        """Run the viewer bot with parallel browsers"""
        self.is_running = True
        task_stop_flags[task_id] = False
        
        running_tasks[task_id] = {
            'status': 'running',
            'current': 0,
            'total': self.iterations,
            'message': f'Starting {self.parallel_browsers} browsers...'
        }
        
        try:
            print(f"Starting {self.parallel_browsers} parallel browsers for {self.iterations} visits...")
            
            iterations_per_worker = self.iterations // self.parallel_browsers
            remainder = self.iterations % self.parallel_browsers
            
            with ThreadPoolExecutor(max_workers=self.parallel_browsers) as executor:
                futures = []
                for i in range(self.parallel_browsers):
                    # Distribute remainder among first workers
                    iters = iterations_per_worker + (1 if i < remainder else 0)
                    futures.append(executor.submit(self.worker, i + 1, iters, task_id))
                
                # Wait for all to complete
                for future in as_completed(futures):
                    result = future.result()
                    print(result)
            
            # Check if stopped or completed
            if task_stop_flags.get(task_id, False):
                running_tasks[task_id] = {
                    'status': 'stopped',
                    'current': self.current_iteration,
                    'total': self.iterations,
                    'message': 'Task stopped by user'
                }
            else:
                running_tasks[task_id] = {
                    'status': 'completed',
                    'current': self.iterations,
                    'total': self.iterations,
                    'message': f'✅ Completed all {self.iterations} visits!'
                }
            
            print(f"✅ Finished all {self.iterations} iterations")
            
        except Exception as e:
            print(f"Error during execution: {e}")
            running_tasks[task_id] = {
                'status': 'error',
                'current': self.current_iteration,
                'total': self.iterations,
                'message': f'Error: {str(e)}'
            }
        finally:
            # Cleanup
            if task_id in active_drivers:
                for driver in active_drivers[task_id]:
                    try:
                        driver.quit()
                    except:
                        pass
                del active_drivers[task_id]
            
            if task_id in task_stop_flags:
                del task_stop_flags[task_id]
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False

@app.post("/api/start", response_model=BotStartResponse)
async def start_bot(request: BotStartRequest):
    """Start the viewer bot"""
    
    # Generate task ID
    task_id = f"task_{int(time.time())}"
    
    # Create and start bot
    bot = ViewerBot(request.url, request.iterations, request.parallel_browsers)
    
    # Run in separate thread
    thread = threading.Thread(target=bot.run, args=(task_id,))
    thread.daemon = True
    thread.start()
    
    return BotStartResponse(
        taskId=task_id,
        message="Bot started successfully",
        url=request.url,
        iterations=request.iterations,
        parallel_browsers=request.parallel_browsers
    )

@app.get("/api/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str):
    """Get the status of a running task"""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = running_tasks[task_id]
    return TaskStatus(**task_data)

@app.post("/api/stop/{task_id}")
async def stop_bot(task_id: str):
    """Stop a running task"""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Set stop flag
    if running_tasks[task_id]['status'] == 'running':
        task_stop_flags[task_id] = True
        running_tasks[task_id]['status'] = 'stopping'
        running_tasks[task_id]['message'] = 'Stopping all browsers...'
        
        # Force close all browsers immediately
        if task_id in active_drivers:
            for driver in active_drivers[task_id]:
                try:
                    driver.quit()
                    print(f"Force closed browser for task {task_id}")
                except Exception as e:
                    print(f"Error force closing browser: {e}")
    
    return {"message": "Stop signal sent to all browsers"}

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", message="Viewer Bot API is running")

@app.get("/api/cleanup")
async def cleanup_resources():
    """Force cleanup all active browser instances (emergency memory cleanup)"""
    closed_count = 0
    errors = []
    
    for task_id, drivers in list(active_drivers.items()):
        if isinstance(drivers, list):
            for driver in drivers:
                try:
                    driver.quit()
                    closed_count += 1
                    print(f"Cleaned up browser for task {task_id}")
                except Exception as e:
                    errors.append(f"Task {task_id}: {str(e)}")
                    print(f"Error cleaning up task {task_id}: {e}")
        else:
            # Handle old single driver format
            try:
                drivers.quit()
                closed_count += 1
                print(f"Cleaned up browser for task {task_id}")
            except Exception as e:
                errors.append(f"Task {task_id}: {str(e)}")
                print(f"Error cleaning up task {task_id}: {e}")
        
        del active_drivers[task_id]
    
    return {
        "message": f"Cleanup completed. Closed {closed_count} browser(s)",
        "closed": closed_count,
        "errors": errors if errors else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)