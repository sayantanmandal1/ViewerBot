# Viewer Bot Application

A full-stack web application that automates website visits using Selenium WebDriver. Built with Next.js frontend and FastAPI backend.

## Features

- 🚀 Modern Next.js interface with Tailwind CSS
- 📊 Real-time progress tracking
- ⚙️ Customizable delay settings
- 🛑 Start/stop functionality
- 📱 Responsive design
- 🎨 Beautiful gradient UI with smooth animations

## Project Structure

```
viewer-bot/
├── backend/
│   ├── app.py              # FastAPI backend
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── app/
│   │   ├── page.tsx        # Main viewer bot component
│   │   ├── layout.tsx      # Root layout
│   │   └── globals.css     # Tailwind CSS
│   └── package.json        # Next.js dependencies
├── try.py                  # Original script
└── README.md
```

## Setup Instructions

### Option 1: Docker Deployment (Recommended for Production)

#### Quick Start with Docker Compose
```bash
cd backend
docker-compose up --build
```

The API will be available at `http://localhost:8000`

#### Manual Docker Build
```bash
cd backend
docker build -t viewer-bot-api .
docker run -p 8000:8000 viewer-bot-api
```

### Option 2: Local Development Setup

#### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
source venv/bin/activate  # On Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the FastAPI server:
```bash
python app.py
```

The backend will be available at `http://localhost:8000`

#### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

1. Open your browser and go to `http://localhost:3000`
2. Enter the website URL you want to visit
3. Set the number of views you want to generate
4. Adjust the min/max delay between visits (default: 1-5 seconds)
5. Click "Start Bot" to begin
6. Monitor progress in real-time with the animated progress bar
7. Click "Stop Bot" to halt the process

## API Endpoints

- `POST /api/start` - Start a new bot task
- `GET /api/status/{task_id}` - Get task status
- `POST /api/stop/{task_id}` - Stop a running task
- `GET /api/health` - Health check
- `GET /docs` - FastAPI automatic documentation

## Tech Stack

### Frontend
- **Next.js 16** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **Axios** - HTTP client

### Backend
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **Selenium** - Web automation
- **Uvicorn** - ASGI server

## Requirements

### For Docker Deployment (Recommended)
- Docker and Docker Compose
- 2GB+ RAM for Chrome in container
- Internet connection for downloading Chrome/ChromeDriver

### For Local Development
- Python 3.7+
- Node.js 18+
- Chrome browser installed (for local development only)

## Docker Features

The Docker setup includes:
- ✅ **Latest Chrome & ChromeDriver** - Automatically installed and configured
- ✅ **Headless operation** - Optimized for server environments
- ✅ **Security hardened** - Runs as non-root user with minimal privileges
- ✅ **Health checks** - Built-in monitoring and auto-restart
- ✅ **Resource limits** - Configurable CPU/memory constraints
- ✅ **Persistent storage** - Chrome data preserved across restarts
- ✅ **Production ready** - Suitable for cloud deployment

## Important Notes

- Use this tool responsibly and in accordance with website terms of service
- The bot runs in headless mode for better performance
- Maximum 10,000 iterations per session for safety
- Minimum delay of 0.1 seconds between requests
- Built with modern web technologies for optimal performance

## Development

To run in development mode:

```bash
# Backend (Terminal 1)
cd backend
python app.py

# Frontend (Terminal 2)
cd frontend
npm run dev
```

## Troubleshooting

If you encounter Chrome WebDriver issues:
1. Make sure Chrome browser is installed
2. Check that your Chrome profile path is correct in the backend code
3. Try running with minimal Chrome options (fallback is built-in)

## License

This project is for educational purposes only. Use responsibly.