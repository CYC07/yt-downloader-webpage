// src/context/AuthContext.js
import React, { createContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../api'; // Your configured axios instance

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true); // Start as loading

    // Function to check auth status on initial load
    const checkAuthStatus = useCallback(async () => {
        setIsLoading(true);
        try {
            // Use the /api/auth/status/ endpoint we created in Django
            const response = await apiClient.get('/auth/status/');
            if (response.data.isAuthenticated) {
                setUser({ username: response.data.username });
                setIsAuthenticated(true);
            } else {
                setUser(null);
                setIsAuthenticated(false);
            }
        } catch (error) {
            console.error("Auth check failed:", error);
            setUser(null);
            setIsAuthenticated(false);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Check status when the provider mounts
    useEffect(() => {
        checkAuthStatus();
    }, [checkAuthStatus]);

    // Login function
    const login = async (username, password) => {
        setIsLoading(true);
        try {
            const response = await apiClient.post('/auth/login/', { username, password });
            setUser({ username: response.data.username });
            setIsAuthenticated(true);
            setIsLoading(false);
            return true; // Indicate success
        } catch (error) {
            console.error("Login failed:", error.response?.data || error.message);
            setUser(null);
            setIsAuthenticated(false);
            setIsLoading(false);
            throw error; // Re-throw error to be caught in component
        }
    };

    // Logout function
    const logout = async () => {
        setIsLoading(true);
        try {
            await apiClient.post('/auth/logout/');
        } catch (error) {
            console.error("Logout failed:", error.response?.data || error.message);
            // Still proceed to clear local state even if backend fails
        } finally {
            setUser(null);
            setIsAuthenticated(false);
            setIsLoading(false);
            // Optionally redirect here or let the component handle it
        }
    };

    // Value provided to consuming components
    const value = {
        user,
        isAuthenticated,
        isLoading,
        login,
        logout,
        checkAuthStatus // Expose if needed for manual refresh
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};