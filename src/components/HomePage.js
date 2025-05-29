// src/components/HomePage.js
import React, { useState, useEffect, useContext } from 'react';
import apiClient from '../api';
import { AuthContext } from '../context/AuthContext'; // Assuming you create this

function HomePage() {
    const [url, setUrl] = useState('');
    const [format, setFormat] = useState('mp4');
    const [taskId, setTaskId] = useState(null);
    const [taskStatus, setTaskStatus] = useState(null);
    const [taskResult, setTaskResult] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { user } = useContext(AuthContext); // Get user info if needed

    // Poll for task status
    useEffect(() => {
        let intervalId;
        if (taskId && taskStatus !== 'SUCCESS' && taskStatus !== 'FAILURE') {
            intervalId = setInterval(async () => {
                try {
                    console.log(`Checking status for task: ${taskId}`);
                    const response = await apiClient.get(`/task_status/${taskId}/`);
                    console.log('Status Response:', response.data);
                    setTaskStatus(response.data.status);
                    setTaskResult(response.data); // Store the full result object

                    if (response.data.status === 'SUCCESS' || response.data.status === 'FAILURE') {
                        clearInterval(intervalId);
                        setTaskId(null); // Reset task ID for new download
                        setLoading(false);
                        if (response.data.status === 'FAILURE') {
                            setError(response.data?.info?.status || response.data?.result?.status || 'Download failed.');
                        } else {
                            setError(''); // Clear previous errors on success
                        }
                    } else {
                         // Update loading/progress message based on taskResult.info
                        setError(''); // Clear error while pending/progressing
                    }
                } catch (err) {
                    console.error("Error fetching task status:", err);
                    setError('Error checking download status.');
                    clearInterval(intervalId);
                    setLoading(false);
                }
            }, 3000); // Poll every 3 seconds
        }

        return () => clearInterval(intervalId); // Cleanup on unmount or when task changes
    }, [taskId, taskStatus]);

    const handleDownload = async (e) => {
        e.preventDefault();
        setError('');
        setTaskStatus(null);
        setTaskResult(null);
        setLoading(true);

        try {
            const response = await apiClient.post('/download/', { url, format });
            setTaskId(response.data.task_id);
            setTaskStatus('PENDING'); // Initial status
             console.log("Task ID:", response.data.task_id);
        } catch (err) {
            console.error("Download request error:", err.response?.data || err.message);
            setError(err.response?.data?.error || 'Failed to start download.');
            setLoading(false);
        }
    };

    // Function to trigger browser download
    const triggerBrowserDownload = (fileUrl, filename) => {
         const link = document.createElement('a');
         // Construct the full URL if the backend returns a relative path
         const fullUrl = new URL(fileUrl, apiClient.defaults.baseURL.replace('/api', '')).href; // Adjust base URL as needed
         link.href = fullUrl;
         link.setAttribute('download', filename || 'download'); // Use filename from backend if available
         document.body.appendChild(link);
         link.click();
         document.body.removeChild(link);
    };


    return (
        <div>
            <h2>Download Video/Audio</h2>
            <p>Welcome, {user?.username}!</p>
            <form onSubmit={handleDownload}>
                <div>
                    <label htmlFor="url">Video URL:</label>
                    <input
                        type="url"
                        id="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        required
                        placeholder="Enter URL from YouTube, Vimeo, etc."
                    />
                </div>
                <div>
                    <label htmlFor="format">Format:</label>
                    <select id="format" value={format} onChange={(e) => setFormat(e.target.value)}>
                        <option value="mp4">MP4 (Video)</option>
                        <option value="mp3">MP3 (Audio)</option>
                    </select>
                </div>
                <button type="submit" disabled={loading || taskId}>
                    {loading ? 'Processing...' : 'Download'}
                </button>
            </form>

            {error && <p style={{ color: 'red' }}>Error: {error}</p>}

            {taskResult && (
                 <div>
                     <h3>Download Status</h3>
                     <p>Status: {taskResult.status}</p>
                     {taskResult.info?.status && <p>Details: {taskResult.info.status}</p>}
                     {taskResult.status === 'PROGRESS' && taskResult.info?.progress !== undefined && (
                         <p>Progress: {taskResult.info.progress}%</p>
                     )}
                     {taskResult.status === 'SUCCESS' && taskResult.info?.file_url && (
                         <div>
                             <p>Download complete!</p>
                              {/* Option 1: Direct Link */}
                              {/*
                              <a
                                 href={new URL(taskResult.info.file_url, apiClient.defaults.baseURL.replace('/api', '')).href}
                                 target="_blank"
                                 rel="noopener noreferrer"
                                 download={taskResult.info.filename || 'download'} >
                                    Download {taskResult.info.filename || 'File'}
                                </a>
                              */}
                              {/* Option 2: Button to trigger download via JS */}
                              <button onClick={() => triggerBrowserDownload(taskResult.info.file_url, taskResult.info.filename)}>
                                   Click to Download {taskResult.info.filename || 'File'}
                              </button>
                         </div>
                     )}
                 </div>
            )}
        </div>
    );
}

export default HomePage;