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
import os
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
        
    def run(self, task_id):
        """Run the viewer bot with progress tracking"""
        self.is_running = True
        running_tasks[task_id] = {
            'status': 'running',
            'current': 0,
            'total': self.iterations,
            'message': 'Starting browser...'
        }
        
        # Chrome options for Docker environment
        chrome_options = Options()
        
        # Essential Chrome arguments for Docker/headless environment
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-field-trial-config")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--remote-debugging-port=9222")
        
        # Use a temporary user data directory in Docker
        chrome_options.add_argument("--user-data-dir=/app/chrome-data")
        chrome_options.add_argument("--profile-directory=Default")
        
        # Additional performance optimizations
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
        
        # Set user agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Prefs to disable notifications, location, etc.
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2
            }
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Exclude automation switches
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Try to create Chrome driver
            driver = webdriver.Chrome(options=chrome_options)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
        except Exception as e:
            print(f"Failed to create Chrome driver: {e}")
            running_tasks[task_id] = {
                'status': 'error',
                'current': 0,
                'total': self.iterations,
                'message': f'Failed to start browser: {str(e)}'
            }
            return
        
        try:
            for i in range(self.iterations):
                if not self.is_running:
                    break
                    
                driver.get(self.url)
                self.current_iteration = i + 1
                
                delay = random.uniform(self.min_delay, self.max_delay)
                
                # Update progress
                running_tasks[task_id] = {
                    'status': 'running',
                    'current': self.current_iteration,
                    'total': self.iterations,
                    'message': f'Visit {self.current_iteration}/{self.iterations} - Next delay: {delay:.2f}s'
                }
                
                time.sleep(delay)
                
        except Exception as e:
            running_tasks[task_id] = {
                'status': 'error',
                'current': self.current_iteration,
                'total': self.iterations,
                'message': f'Error: {str(e)}'
            }
        finally:
            try:
                driver.quit()
            except:
                pass
            
            if self.is_running:
                running_tasks[task_id] = {
                    'status': 'completed',
                    'current': self.iterations,
                    'total': self.iterations,
                    'message': f'✅ Completed all {self.iterations} visits!'
                }
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