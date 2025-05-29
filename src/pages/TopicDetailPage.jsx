// src/pages/TopicDetailPage.jsx
import React, { useState, useEffect, useContext } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import apiClient from '../api';
// import { AuthContext } from '../context/AuthContext.jsx'; // Uncomment if you need user info

function TopicDetailPage() {
    const { topicId } = useParams();
    const [topic, setTopic] = useState(null);
    const [posts, setPosts] = useState([]); // Initialize as an empty array
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [postError, setPostError] = useState('');
    const [newPostContent, setNewPostContent] = useState('');
    const [isSubmittingPost, setIsSubmittingPost] = useState(false);
    // const { user } = useContext(AuthContext);
    // const navigate = useNavigate(); // Keep if you plan to navigate after some action

    // Function to fetch topic details and posts from the backend
    const fetchTopicDetails = async () => {
        setIsLoading(true);
        setError('');
        try {
            const response = await apiClient.get(`/forum/topics/${topicId}/`);
            setTopic(response.data);
            setPosts(response.data.posts || []); // Set posts from API, default to empty if none
        } catch (err) {
            console.error("Failed to fetch topic details:", err);
            if (err.response && err.response.status === 404) {
                setError('Topic not found.');
            } else {
                setError('Could not load topic details. Please try again later.');
            }
            setTopic(null);
            setPosts([]); // Clear posts on error too
        } finally {
            setIsLoading(false);
        }
    };

    // Fetch data when component mounts or topicId changes
    useEffect(() => {
        fetchTopicDetails();
    }, [topicId]);

    const handlePostSubmit = async (e) => {
        e.preventDefault();
        if (!newPostContent.trim()) {
            setPostError('Reply content cannot be empty.');
            return;
        }
        setIsSubmittingPost(true);
        setPostError('');

        try {
            const response = await apiClient.post(`/forum/topics/${topicId}/posts/`, {
                content: newPostContent
            });
            // Add the new post to the local state for immediate UI update
            // To ensure correct order, it's often better to re-fetch or sort if backend returns all posts
            // For simplicity here, adding to the end (or beginning) is common.
            // If your backend returns posts sorted by created_at ascending, add to end.
            setPosts(prevPosts => [...prevPosts, response.data]);
            // Or if you prefer new posts at the top (and backend returns created_at descending for topic detail):
            // setPosts(prevPosts => [response.data, ...prevPosts]);

            setNewPostContent('');
        } catch (err) {
            console.error("Failed to submit post:", err.response?.data || err.message);
            setPostError(err.response?.data?.content?.[0] || err.response?.data?.error || 'Could not submit reply.');
        } finally {
            setIsSubmittingPost(false);
        }
    };

    if (isLoading) return <div style={{ textAlign: 'center', marginTop: '20px' }}>Loading topic details...</div>;
    if (error) return <div style={{ color: 'red', textAlign: 'center', marginTop: '20px' }}>Error: {error} <br/> <Link to="/forum">Back to Forum</Link></div>;
    if (!topic) return <div style={{ textAlign: 'center', marginTop: '20px' }}>Topic not found. <Link to="/forum">Back to Forum</Link></div>;

    return (
        <div style={{ maxWidth: '800px', margin: '20px auto', padding: '20px', background: '#2c2c2c', borderRadius: '8px', color: '#eee' }}>
            <Link to="/forum" style={{ display: 'inline-block', marginBottom: '15px', color: '#a0cfff', textDecoration: 'none' }}>
                ← Back to All Topics
            </Link>
            <h2>{topic.title}</h2>
            <p style={{ color: '#aaa', fontSize: '0.9em', borderBottom: '1px solid #444', paddingBottom: '10px', marginBottom: '20px' }}>
                Started by: {topic.author?.username || 'Unknown User'} on {new Date(topic.created_at).toLocaleDateString()}
            </p>

            <h3>Posts</h3>
            {posts.length === 0 && <p style={{color: '#888'}}>No posts in this topic yet. Be the first to reply!</p>}
            <ul style={{ listStyle: 'none', padding: 0 }}>
                {posts.map(post => (
                    <li key={post.id} style={{ borderBottom: '1px solid #444', padding: '15px 0' }}>
                        <div style={{whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginBottom: '8px'}}>{post.content}</div>
                        <small style={{ color: '#888' }}>
                            By: {post.author?.username || 'Unknown User'} on {new Date(post.created_at).toLocaleString()}
                        </small>
                    </li>
                ))}
            </ul>

            <hr style={{ margin: '30px 0', borderColor: '#444' }}/>
            <h3>Reply to this Topic</h3>
            {postError && <p style={{ color: 'salmon', marginBottom: '10px' }}>{postError}</p>}
            <form onSubmit={handlePostSubmit} style={{ marginTop: '10px' }}>
                <div>
                    <textarea
                        value={newPostContent}
                        onChange={(e) => setNewPostContent(e.target.value)}
                        placeholder="Write your reply..."
                        rows="5"
                        style={{ width: '98%', marginBottom: '10px', background: '#383838', color: '#eee', border: '1px solid #555', borderRadius: '4px', padding: '10px', resize: 'vertical' }}
                        required
                    />
                </div>
                <button
                    type="submit"
                    disabled={isSubmittingPost}
                    style={{ padding: '10px 20px', backgroundColor: '#6a0dad', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
                >
                    {isSubmittingPost ? 'Posting...' : 'Post Reply'}
                </button>
            </form>
        </div>
    );
}

export default TopicDetailPage;