// src/pages/HomePage.jsx
import React, { useState, useEffect, useContext, useRef } from 'react'; // Added useRef
import apiClient from '../api';
import { AuthContext } from '../context/AuthContext';

function HomePage() {
    // --- Form State ---
    const [url, setUrl] = useState('');
    const [isPlaylist, setIsPlaylist] = useState(false);
    const [availableFormats, setAvailableFormats] = useState([]);
    const [selectedFormatCode, setSelectedFormatCode] = useState('');
    const [fetchingFormats, setFetchingFormats] = useState(false);
    const [formatError, setFormatError] = useState('');
    const [submitError, setSubmitError] = useState(''); // Error specifically for form submission
    const [isSubmitting, setIsSubmitting] = useState(false); // Loading state for form submission

    // --- Downloads List State ---
    // Array to hold info about each download task
    // Example item: { id: taskId, url: '...', formatCode: '...', status: 'PROGRESS', progress: 50, result: null, error: null }
    const [downloads, setDownloads] = useState([]);

    // --- Other Context/State ---
    const { user, isLoading: authLoading } = useContext(AuthContext);

    // Ref to store interval ID to prevent issues with stale state in interval closure
    const intervalRef = useRef(null);

    // --- Polling Logic for ALL Active Downloads ---
    useEffect(() => {
        const pollStatuses = async () => {
            // Get IDs of tasks that are not in a final state
            const activeTasks = downloads.filter(d => d.taskId && d.status !== 'SUCCESS' && d.status !== 'FAILURE');

            if (activeTasks.length === 0) {
                // console.log("Polling: No active tasks.");
                if (intervalRef.current) {
                    // console.log("Polling: Clearing interval.");
                    clearInterval(intervalRef.current);
                    intervalRef.current = null;
                }
                return; // Stop polling if no active tasks
            }

            // console.log(`Polling: Checking status for ${activeTasks.length} tasks.`);
            activeTasks.forEach(async (task) => {
                try {
                    const response = await apiClient.get(`/task_status/${task.taskId}/`);
                    const data = response.data;

                    // Update the specific download item in the state array immutably
                    setDownloads(currentDownloads =>
                        currentDownloads.map(d => {
                            if (d.taskId === task.taskId) {
                                let errorMsg = null;
                                if (data.status === 'FAILURE') {
                                    errorMsg = data.result?.exc_message || data.info?.status || 'Download failed.';
                                }
                                return {
                                    ...d, // Keep existing info
                                    status: data.status,
                                    progress: data.info?.progress, // Get progress from info meta
                                    result: data.result, // Store full result (for success/failure data)
                                    error: errorMsg, // Store specific error message
                                };
                            }
                            return d; // Return other downloads unchanged
                        })
                    );

                } catch (err) {
                    console.error(`Error fetching status for task ${task.taskId}:`, err);
                    // Update the specific task with an error message
                    setDownloads(currentDownloads =>
                        currentDownloads.map(d => {
                            if (d.taskId === task.taskId) {
                                return { ...d, status: 'ERROR_POLLING', error: 'Error checking status.' };
                            }
                            return d;
                        })
                    );
                }
            });
        };

        // Start polling only if there are downloads and no interval is running
        if (downloads.some(d => d.taskId && d.status !== 'SUCCESS' && d.status !== 'FAILURE') && !intervalRef.current) {
            // console.log("Polling: Starting interval.");
            intervalRef.current = setInterval(pollStatuses, 4000); // Poll slightly less frequently (e.g., 4s)
        }

        // Cleanup function
        return () => {
            if (intervalRef.current) {
                // console.log("Polling: Cleanup clearing interval.");
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
        // Rerun when the list of downloads changes (specifically when taskIds/statuses change)
    }, [downloads]);


    // --- Fetch Formats (Remains the same) ---
    const handleFetchFormats = async () => { /* ... */
         if (!url) { setFormatError('Please enter URL.'); return; } setFetchingFormats(true); setFormatError(''); setSubmitError(''); setAvailableFormats([]); setSelectedFormatCode(''); try { const response = await apiClient.post('/get_formats/', { url }); if (response.data?.formats && response.data.formats.length > 0) { setAvailableFormats(response.data.formats); } else { setFormatError('No formats found.'); } } catch (err) { console.error("Fetch formats error:", err.response?.data || err.message); setFormatError(err.response?.data?.error || 'Failed to fetch.'); } finally { setFetchingFormats(false); }
     };

    // --- Handle Download Submission ---
    const handleDownload = async (e) => {
        e.preventDefault();
        if (!selectedFormatCode) { setSubmitError('Please select format.'); return; }
        setSubmitError(''); setFormatError(''); setIsSubmitting(true); // Indicate submission attempt

        const selectedFormat = availableFormats.find(f => f.code === selectedFormatCode);
        let formatType = 'video';
        if (selectedFormatCode.includes('_convert_')) { formatType = 'audio'; }
        else if (selectedFormat?.type === 'audio') { formatType = 'audio'; }

        const requestData = {
            url,
            format_code: selectedFormatCode,
            format_type: formatType,
            is_playlist: isPlaylist
        };

        try {
            const response = await apiClient.post('/download/', requestData);
            const newTaskId = response.data.task_id;

            // Add new download to the beginning of the list
            setDownloads(prevDownloads => [
                {
                    id: newTaskId, // Use task ID as unique key for list rendering
                    taskId: newTaskId,
                    url: url, // Store URL for display
                    formatCode: selectedFormatCode, // Store format for display
                    status: 'PENDING', // Initial status
                    progress: 0,
                    result: null,
                    error: null
                },
                ...prevDownloads // Add existing downloads after the new one
            ]);

            // Clear form for next input (optional)
            // setUrl('');
            // setAvailableFormats([]);
            // setSelectedFormatCode('');
            // setIsPlaylist(false);

            console.log("Download task started:", newTaskId);

        } catch (err) {
            console.error("Download request error:", err.response?.data || err.message);
            setSubmitError(err.response?.data?.error || 'Failed to start download.');
        } finally {
             setIsSubmitting(false); // Finish submission attempt
        }
    };

    // --- triggerBrowserDownload (Remains the same) ---
    const triggerBrowserDownload = (fileUrl, filename) => { /* ... */
         if (!fileUrl) return; const link=document.createElement('a'); const base = apiClient.defaults.baseURL.replace('/api',''); const url = new URL(fileUrl, base).href; link.href=url; link.setAttribute('download',filename||'download'); link.setAttribute('target','_blank'); link.setAttribute('rel','noopener noreferrer'); document.body.appendChild(link); link.click(); document.body.removeChild(link);
    };

    // --- Function to remove a download item from the list (optional) ---
    const removeDownloadItem = (taskIdToRemove) => {
         setDownloads(prevDownloads => prevDownloads.filter(d => d.taskId !== taskIdToRemove));
    };


    if (authLoading) return <div>Loading user...</div>;

    // --- Render UI ---
    return (
        <div>
            <h2>Download Video/Audio</h2>
            {user && <p>Welcome, {user.username}!</p>}

            {/* --- Download Form --- */}
            <form onSubmit={handleDownload} style={{ marginBottom: '30px', paddingBottom: '20px', borderBottom: '1px solid #ccc' }}>
                <div><label>URL:</label><input type="url" value={url} onChange={(e) => setUrl(e.target.value)} required placeholder="Enter URL" style={{ width: '400px', marginBottom: '10px' }}/><button type="button" onClick={handleFetchFormats} disabled={fetchingFormats || !url || isSubmitting}>{fetchingFormats ? 'Fetching...' : 'Fetch Formats'}</button></div>
                {formatError && <p style={{ color: 'orange', marginTop: '5px' }}>{formatError}</p>}
                {availableFormats.length > 0 && ( <div style={{ marginBottom: '10px' }}><label>Format:</label><select value={selectedFormatCode} onChange={(e) => setSelectedFormatCode(e.target.value)} required ><option value="" disabled>-- Select --</option>{availableFormats.map(f => (<option key={f.code} value={f.code}>{f.description}</option>))} </select></div>)}
                <div style={{ marginBottom: '10px' }}><input type="checkbox" id="playlistCheckbox" checked={isPlaylist} onChange={(e) => setIsPlaylist(e.target.checked)} style={{marginRight:'5px'}} /><label htmlFor="playlistCheckbox">Download playlist</label></div>
                <button type="submit" disabled={isSubmitting || fetchingFormats || !selectedFormatCode}>
                    {isSubmitting ? 'Starting...' : 'Start Download'}
                </button>
                 {submitError && <p style={{ color: 'red', marginTop: '5px' }}>{submitError}</p>}
            </form>

            {/* --- Downloads List Display --- */}
            {downloads.length > 0 && (
                <div>
                    <h3>Download Queue / History</h3>
                    <ul style={{ listStyle: 'none', padding: 0 }}>
                        {downloads.map(download => (
                            <li key={download.id} style={{ border: '1px solid #eee', padding: '10px', marginBottom: '10px', background: '#f9f9f9' }}>
                                <div style={{ marginBottom: '5px' }}>
                                     <small>URL: {download.url}</small><br/>
                                     <small>Format: {download.formatCode}</small>
                                </div>
                                <div><strong>Status:</strong> {download.status}</div>

                                {/* Progress Bar */}
                                {download.status === 'PROGRESS' && download.progress !== undefined && (
                                    <div style={{marginTop: '5px'}}>
                                        <progress value={download.progress} max="100" style={{ width: '80%' }} />
                                        <span> {download.progress}%</span>
                                    </div>
                                )}

                                {download.status === 'SUCCESS' && download.result && (
                                    <div style={{ marginTop: '10px' }}>
                                        <strong className="status-complete">Complete!</strong><br/> {/* Added class */}
                                        {/* ... rest of success display ... */}
                                    </div>
                                )}
                                {download.status === 'FAILURE' && (
                                    <div style={{ marginTop: '10px' }}>
                                        <strong className="status-failed">Failed!</strong><br/> {/* Added class */}
                                        <span>Reason: {download.error || 'Unknown error'}</span>
                                        {/* ... rest of failure display ... */}
                                    </div>
                                )}

                                 {/* Error during polling */}
                                 {download.status === 'ERROR_POLLING' && (
                                      <div style={{ marginTop: '10px' }}>
                                          <strong style={{ color: 'red' }}>Error checking status.</strong><br/>
                                          <span>{download.error}</span>
                                           <button onClick={() => removeDownloadItem(download.taskId)} style={{ marginLeft: '10px', fontSize: '0.8em', color: 'grey' }}>Clear</button>
                                      </div>
                                  )}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

        </div> // End main container
    );
}

export default HomePage;