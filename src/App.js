// src/App.js
import React, { useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';
import { AuthProvider, AuthContext } from './context/AuthContext';
import HomePage from './pages/HomePage'; // Assuming HomePage is moved to pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProtectedRoute from './components/ProtectedRoute';
import './App.css'; // Optional: for basic styling

// Simple Navbar component
function Navigation() {
    const { isAuthenticated, user, logout } = useContext(AuthContext);
    const navigate = useNavigate();

    const handleLogout = async () => {
        await logout();
        navigate('/login'); // Redirect to login after logout
    };

    return (
        <nav style={{ background: '#eee', padding: '10px', marginBottom: '20px' }}>
            <Link to="/" style={{ marginRight: '10px' }}>Home</Link>
            {!isAuthenticated ? (
                <>
                    <Link to="/login" style={{ marginRight: '10px' }}>Login</Link>
                    <Link to="/register">Register</Link>
                </>
            ) : (
                <>
                    <span style={{ marginRight: '15px' }}>Welcome, {user?.username}!</span>
                    <button onClick={handleLogout}>Logout</button>
                </>
            )}
        </nav>
    );
}


function App() {
    return (
        <AuthProvider> {/* Wrap the entire app in the AuthProvider */}
            <Router>
                <Navigation /> {/* Render the Navbar */}
                <div className="container" style={{ padding: '0 20px' }}> {/* Optional container */}
                    <Routes>
                        {/* Public Routes */}
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />

                        {/* Protected Routes */}
                        <Route element={<ProtectedRoute />}>
                             {/* All routes nested inside ProtectedRoute require login */}
                            <Route path="/" element={<HomePage />} />
                            {/* Add other protected routes here */}
                            {/* e.g., <Route path="/profile" element={<ProfilePage />} /> */}
                        </Route>

                        {/* Optional: Catch-all for 404 Not Found */}
                        <Route path="*" element={<div><h2>404 Not Found</h2><Link to="/">Go Home</Link></div>} />
                    </Routes>
                </div>
            </Router>
        </AuthProvider>
    );
}

export default App;