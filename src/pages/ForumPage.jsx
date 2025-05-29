// src/pages/ForumPage.jsx
import React, { useState, useEffect, useContext } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import apiClient from '../api';
import { AuthContext } from '../context/AuthContext'; // To check if user is logged in

function ForumPage() {
    const [topics, setTopics] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [newTopicTitle, setNewTopicTitle] = useState('');
    const [isSubmittingTopic, setIsSubmittingTopic] = useState(false);
    const { isAuthenticated } = useContext(AuthContext);
    const navigate = useNavigate();

    useEffect(() => {
        const fetchTopics = async () => {
            setIsLoading(true);
            try {
                const response = await apiClient.get('/forum/topics/');
                setTopics(response.data);
            } catch (err) {
                console.error("Failed to fetch topics:", err);
                setError('Could not load topics. Please try again later.');
            } finally {
                setIsLoading(false);
            }
        };
        if (isAuthenticated) { // Only fetch if authenticated
            fetchTopics();
        }
    }, [isAuthenticated]);

    const handleCreateTopic = async (e) => {
        e.preventDefault();
        if (!newTopicTitle.trim()) {
            setError('Topic title cannot be empty.');
            return;
        }
        setIsSubmittingTopic(true);
        setError('');
        try {
            const response = await apiClient.post('/forum/topics/', { title: newTopicTitle });
            // Navigate to the new topic's detail page
            navigate(`/forum/topics/${response.data.id}`);
            setNewTopicTitle(''); // Clear input
        } catch (err) {
            console.error("Failed to create topic:", err.response?.data || err.message);
            setError(err.response?.data?.title?.[0] || err.response?.data?.error || 'Could not create topic.');
        } finally {
            setIsSubmittingTopic(false);
        }
    };

    if (isLoading) return <div>Loading topics...</div>;

    return (
        <div>
            <h2>Discussion Forum</h2>
            {error && <p style={{ color: 'red' }}>{error}</p>}

            {isAuthenticated && (
                <form onSubmit={handleCreateTopic} style={{ marginBottom: '20px', padding: '10px', border: '1px solid #ccc' }}>
                    <h3>Create New Topic</h3>
                    <div>
                        <input
                            type="text"
                            value={newTopicTitle}
                            onChange={(e) => setNewTopicTitle(e.target.value)}
                            placeholder="Enter topic title"
                            style={{ width: '70%', marginRight: '10px' }}
                            required
                        />
                        <button type="submit" disabled={isSubmittingTopic}>
                            {isSubmittingTopic ? 'Creating...' : 'Create Topic'}
                        </button>
                    </div>
                </form>
            )}

            <h3>Topics</h3>
            {topics.length === 0 && !isLoading && <p>No topics yet. Be the first to create one!</p>}
            <ul style={{ listStyle: 'none', padding: 0 }}>
                {topics.map(topic => (
                    <li key={topic.id} style={{ borderBottom: '1px solid #eee', padding: '10px 0' }}>
                        <Link to={`/forum/topics/${topic.id}`} style={{ fontSize: '1.2em', textDecoration: 'none' }}>
                            {topic.title}
                        </Link>
                        <div style={{ fontSize: '0.8em', color: '#777' }}>
                            Started by: {topic.author.username} on {new Date(topic.created_at).toLocaleDateString()}
                            {' | '}
                            Posts: {topic.post_count}
                            {' | '}
                            Last activity: {new Date(topic.latest_post_at).toLocaleString()}
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default ForumPage;