'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';

// Backend API URL - Change this to your deployed backend URL
const API_BASE_URL = 'https://viewerbot-8kru.onrender.com'; // For local development
// const API_BASE_URL = 'https://your-backend-url.com'; // For production

interface FormData {
  url: string;
  iterations: number;
}

interface TaskStatus {
  status: string;
  current: number;
  total: number;
  message: string;
}

export default function ViewerBot() {
  const [formData, setFormData] = useState<FormData>({
    url: '',
    iterations: 100
  });
  
  const [currentTask, setCurrentTask] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Poll for task status
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (currentTask && taskStatus?.status === 'running') {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/api/status/${currentTask}`);
          setTaskStatus(response.data);
          
          if (response.data.status !== 'running') {
            setCurrentTask(null);
          }
        } catch (err) {
          console.error('Error fetching status:', err);
        }
      }, 1000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentTask, taskStatus?.status]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'url' ? value : Number(value)
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/start`, formData);
      setCurrentTask(response.data.taskId);
      setTaskStatus({
        status: 'running',
        current: 0,
        total: formData.iterations,
        message: 'Starting...'
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start bot');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStop = async () => {
    if (!currentTask) return;
    
    try {
      await axios.post(`${API_BASE_URL}/api/stop/${currentTask}`);
    } catch (err) {
      console.error('Error stopping task:', err);
    }
  };

  const getProgressPercentage = () => {
    if (!taskStatus) return 0;
    return Math.round((taskStatus.current / taskStatus.total) * 100);
  };

  const getStatusColor = () => {
    if (!taskStatus) return 'bg-gray-500';
    switch (taskStatus.status) {
      case 'running': return 'bg-green-500';
      case 'completed': return 'bg-blue-500';
      case 'error': return 'bg-red-500';
      case 'stopped': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  const getProgressColor = () => {
    if (!taskStatus) return 'bg-gray-500';
    switch (taskStatus.status) {
      case 'running': return 'bg-green-500';
      case 'completed': return 'bg-blue-500';
      case 'error': return 'bg-red-500';
      case 'stopped': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 via-purple-600 to-purple-800 flex items-center justify-center p-5">
      <div className="bg-white rounded-3xl shadow-2xl p-10 max-w-2xl w-full">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-black mb-3">🚀 Viewer Bot</h1>
          <p className="text-black text-lg">Increase website views automatically</p>
        </div>

        <div className="space-y-8">
          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* URL Input */}
            <div>
              <label htmlFor="url" className="block text-sm font-semibold text-black mb-2">
                Website URL
              </label>
              <input
                type="text"
                id="url"
                name="url"
                value={formData.url}
                onChange={handleInputChange}
                placeholder="https://example.com or github.com/username"
                required
                disabled={isLoading || !!currentTask}
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 disabled:bg-gray-50 disabled:cursor-not-allowed text-black"
              />
            </div>

            {/* Iterations Input */}
            <div>
              <label htmlFor="iterations" className="block text-sm font-semibold text-black mb-2">
                Number of Views
              </label>
              <input
                type="number"
                id="iterations"
                name="iterations"
                value={formData.iterations}
                onChange={handleInputChange}
                min="1"
                max="10000"
                required
                disabled={isLoading || !!currentTask}
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-300 disabled:bg-gray-50 disabled:cursor-not-allowed text-black"
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-lg">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <span className="text-red-500">⚠️</span>
                  </div>
                  <div className="ml-3">
                    <p className="text-black text-sm">{error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex justify-center">
              {!currentTask ? (
                <button 
                  type="submit" 
                  disabled={isLoading}
                  className="px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-xl hover:from-blue-600 hover:to-purple-700 focus:ring-4 focus:ring-blue-200 transition-all duration-300 transform hover:-translate-y-1 hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none min-w-[160px]"
                >
                  {isLoading ? '🔄 Starting...' : '🚀 Start Bot'}
                </button>
              ) : (
                <button 
                  type="button" 
                  onClick={handleStop}
                  className="px-8 py-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-xl hover:from-red-600 hover:to-red-700 focus:ring-4 focus:ring-red-200 transition-all duration-300 transform hover:-translate-y-1 hover:shadow-lg min-w-[160px]"
                >
                  ⏹️ Stop Bot
                </button>
              )}
            </div>
          </form>

          {/* Status Panel */}
          {taskStatus && (
            <div className="bg-gray-50 rounded-2xl p-6 border border-gray-200">
              {/* Status Header */}
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-semibold text-black">Bot Status</h3>
                <span className={`px-3 py-1 rounded-full text-white text-xs font-semibold uppercase ${getStatusColor()}`}>
                  {taskStatus.status}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="mb-4">
                <div className="flex justify-between text-sm text-black mb-2">
                  <span>{taskStatus.current} / {taskStatus.total} views</span>
                  <span>{getProgressPercentage()}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${getProgressColor()}`}
                    style={{ width: `${getProgressPercentage()}%` }}
                  />
                </div>
              </div>

              {/* Status Message */}
              <div className="text-black text-sm italic">
                {taskStatus.message}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-8 pt-6 border-t border-gray-200">
          <p className="text-black text-sm">Built with Next.js + FastAPI • Use responsibly</p>
        </div>
      </div>
    </div>
  );
}