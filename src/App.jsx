// src/App.jsx
import React, { useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import { AuthProvider, AuthContext } from './context/AuthContext.jsx';
import HomePage from './pages/HomePage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import RegisterPage from './pages/RegisterPage.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import ForumPage from './pages/ForumPage.jsx';
import TopicDetailPage from './pages/TopicDetailPage.jsx';

import './HomePage.css'; // Import your main CSS file

function Navigation() {
    const { isAuthenticated, user, logout } = useContext(AuthContext);
    const navigate = useNavigate();

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    return (
        <nav className="app-navbar">
            <div className="nav-section"> {/* For left-aligned items */}
                <Link to="/">Downloader</Link>
                <Link to="/forum">Forum</Link>
            </div>
            <div className="nav-section"> {/* For right-aligned items */}
                {!isAuthenticated ? (
                    <>
                        <Link to="/login">Login</Link>
                        <Link to="/register">Register</Link>
                    </>
                ) : (
                    <>
                        {user && <span className="nav-text" style={{color: '#e0c6ff'}}>Welcome, {user.username}!</span>}
                        <button onClick={handleLogout} className="logout-button">Logout</button>
                    </>
                )}
            </div>
        </nav>
    );
}

function App() {
    return (
        <AuthProvider>
            <Router>
                <Navigation /> {/* Navbar is outside the content container for fixed positioning */}
                <div className="app-content-container"> {/* This will hold the scrollable page content */}
                    <Routes>
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />
                        <Route element={<ProtectedRoute />}>
                            <Route path="/" element={<HomePage />} />
                            <Route path="/forum" element={<ForumPage />} />
                            <Route path="/forum/topics/:topicId" element={<TopicDetailPage />} />
                        </Route>
                        <Route path="*" element={
                            <div style={{ textAlign: 'center', marginTop: '50px', flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
                                <h2>404 - Page Not Found</h2>
                                <Link to="/" style={{color: '#a0cfff', fontSize: '1.2rem'}}>Go to Downloader</Link>
                            </div>
                        }/>
                    </Routes>
                </div>
            </Router>
        </AuthProvider>
    );
}

export default App;