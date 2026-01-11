import os
import platform
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import random
import time
import asyncio
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from typing import Optional

app = FastAPI(title="Viewer Bot API", description="A simple viewer bot for websites", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class BotStartRequest(BaseModel):
    url: str
    iterations: int = 100
    minDelay: float = 1.0
    maxDelay: float = 5.0
    
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
    
    @validator('minDelay', 'maxDelay')
    def validate_delays(cls, v):
        if v < 0.1:
            raise ValueError('Delay must be at least 0.1 seconds')
        return v
    
    @validator('maxDelay')
    def validate_max_delay(cls, v, values):
        if 'minDelay' in values and v < values['minDelay']:
            raise ValueError('maxDelay must be greater than or equal to minDelay')
        return v

class BotStartResponse(BaseModel):
    taskId: str
    message: str
    url: str
    iterations: int
    minDelay: float
    maxDelay: float

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

class ViewerBot:
    def __init__(self, url, iterations, min_delay=1, max_delay=5):
        self.url = url
        self.iterations = iterations
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.is_running = False
        self.current_iteration = 0
        
    def get_chrome_options(self):
        """Get Chrome options based on environment"""
        chrome_options = Options()
        
        # Detect if running in Docker
        is_docker = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)
        is_windows = platform.system() == 'Windows'
        
        print(f"Environment: Docker={is_docker}, Windows={is_windows}")
        
        # Basic headless setup
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Essential flags that don't break functionality
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Set user data directory based on environment
        if is_docker:
            chrome_options.add_argument("--user-data-dir=/app/chrome-data")
            chrome_options.add_argument("--remote-debugging-port=9222")
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        elif is_windows:
            # Use a temporary directory for Windows
            import tempfile
            temp_dir = tempfile.mkdtemp()
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            chrome_options.add_argument("--remote-debugging-port=9222")
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebDriver/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        else:
            # Linux/Mac
            chrome_options.add_argument("--user-data-dir=/tmp/chrome-data")
            chrome_options.add_argument("--remote-debugging-port=9222")
            user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        chrome_options.add_argument(f"--user-agent={user_agent}")
        chrome_options.add_argument("--profile-directory=Default")
        
        # IMPORTANT: Keep JavaScript and images enabled for proper analytics
        # DO NOT add: --disable-javascript, --disable-images
        
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
        
    def run(self, task_id):
        """Run the viewer bot with progress tracking"""
        self.is_running = True
        running_tasks[task_id] = {
            'status': 'running',
            'current': 0,
            'total': self.iterations,
            'message': 'Starting browser...'
        }
        
        # Get Chrome options for current environment
        chrome_options = self.get_chrome_options()
        
        try:
            # Try to create Chrome driver
            print("Creating Chrome driver...")
            driver = webdriver.Chrome(options=chrome_options)
            
            # Execute script to remove webdriver property (anti-detection)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("Chrome driver created successfully")
            
        except Exception as e:
            print(f"Failed to create Chrome driver: {e}")
            print("Trying with minimal fallback options...")
            
            # Fallback with minimal options (like original try.py)
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--remote-debugging-port=9223")
            
            try:
                driver = webdriver.Chrome(options=chrome_options)
                print("Fallback Chrome driver created successfully")
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                running_tasks[task_id] = {
                    'status': 'error',
                    'current': 0,
                    'total': self.iterations,
                    'message': f'Failed to start browser: {str(fallback_error)}'
                }
                return
        
        try:
            for i in range(self.iterations):
                if not self.is_running:
                    break
                
                # Navigate to the URL
                print(f"[{i+1}/{self.iterations}] Visiting: {self.url}")
                driver.get(self.url)
                
                # Wait for page to load properly (important for analytics)
                time.sleep(3)
                
                # Simulate real user behavior
                try:
                    # Scroll down a bit to simulate reading
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/4);")
                    time.sleep(1)
                    
                    # Scroll to middle
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                    time.sleep(1)
                    
                    # Scroll back to top
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(1)
                except Exception as scroll_error:
                    print(f"Scroll simulation failed: {scroll_error}")
                    pass
                
                self.current_iteration = i + 1
                delay = random.uniform(self.min_delay, self.max_delay)
                
                # Update progress
                running_tasks[task_id] = {
                    'status': 'running',
                    'current': self.current_iteration,
                    'total': self.iterations,
                    'message': f'Visit {self.current_iteration}/{self.iterations} - Next delay: {delay:.2f}s'
                }
                
                print(f"[{i+1}/{self.iterations}] Opened → sleeping for {delay:.2f}s")
                time.sleep(delay)
                
        except Exception as e:
            print(f"Error during execution: {e}")
            running_tasks[task_id] = {
                'status': 'error',
                'current': self.current_iteration,
                'total': self.iterations,
                'message': f'Error: {str(e)}'
            }
        finally:
            try:
                driver.quit()
                print("✅ Browser closed")
            except Exception as quit_error:
                print(f"Error closing browser: {quit_error}")
                pass
            
            if self.is_running:
                running_tasks[task_id] = {
                    'status': 'completed',
                    'current': self.iterations,
                    'total': self.iterations,
                    'message': f'✅ Completed all {self.iterations} visits!'
                }
                print(f"✅ Finished all {self.iterations} iterations")
            else:
                running_tasks[task_id] = {
                    'status': 'stopped',
                    'current': self.current_iteration,
                    'total': self.iterations,
                    'message': 'Task stopped by user'
                }
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False

@app.post("/api/start", response_model=BotStartResponse)
async def start_bot(request: BotStartRequest):
    """Start the viewer bot"""
    
    # Generate task ID
    task_id = f"task_{int(time.time())}"
    
    # Create and start bot
    bot = ViewerBot(request.url, request.iterations, request.minDelay, request.maxDelay)
    
    # Run in separate thread
    thread = threading.Thread(target=bot.run, args=(task_id,))
    thread.daemon = True
    thread.start()
    
    return BotStartResponse(
        taskId=task_id,
        message="Bot started successfully",
        url=request.url,
        iterations=request.iterations,
        minDelay=request.minDelay,
        maxDelay=request.maxDelay
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
    
    # Mark as stopped (the bot will check this flag)
    if running_tasks[task_id]['status'] == 'running':
        running_tasks[task_id]['status'] = 'stopping'
        running_tasks[task_id]['message'] = 'Stopping...'
    
    return {"message": "Stop signal sent"}

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(status="healthy", message="Viewer Bot API is running")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)