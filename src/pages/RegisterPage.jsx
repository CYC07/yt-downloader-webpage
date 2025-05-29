// src/pages/RegisterPage.jsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import apiClient from '../api';

function RegisterPage() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [email, setEmail] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(''); setSuccess(''); setIsSubmitting(true);
        if (!username || !password) {
             setError('Username and password are required.'); setIsSubmitting(false); return;
        }
        try {
            const response = await apiClient.post('/auth/register/', { username, password, email });
            setSuccess(response.data.message + ' You can now log in.');
            setTimeout(() => navigate('/login'), 2500);
        } catch (err) {
            setError(err.response?.data?.error || 'Registration failed. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="auth-page-container">
            <div className="auth-form-wrapper">
                <h2>Register</h2>
                <form onSubmit={handleSubmit}>
                    <div>
                        <label htmlFor="register-username">Username:</label>
                        <input type="text" id="register-username" value={username} onChange={(e) => setUsername(e.target.value)} required />
                    </div>
                     <div>
                        <label htmlFor="register-email">Email (Optional):</label>
                        <input type="email" id="register-email" value={email} onChange={(e) => setEmail(e.target.value)} />
                    </div>
                    <div>
                        <label htmlFor="register-password">Password:</label>
                        <input type="password" id="register-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                    </div>
                    {error && <p className="form-error">{error}</p>}
                    {success && <p className="form-success">{success}</p>}
                    <button type="submit" disabled={isSubmitting}>
                        {isSubmitting ? 'Registering...' : 'Register'}
                    </button>
                </form>
                <p className="switch-auth-link">
                    Already have an account? <Link to="/login">Login here</Link>
                </p>
            </div>
        </div>
    );
}

export default RegisterPage;