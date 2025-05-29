// src/components/ProtectedRoute.js
import React, { useContext } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';

// Option 1: Wrapping specific components (older style)
// const ProtectedRoute = ({ children }) => {
//     const { isAuthenticated, isLoading } = useContext(AuthContext);

//     if (isLoading) {
//         return <div>Loading...</div>; // Or a spinner component
//     }

//     if (!isAuthenticated) {
//         // Redirect them to the /login page, but save the current location they were
//         // trying to go to when they were redirected. This allows us to send them
//         // along to that page after they login, which is a nicer user experience
//         // than dropping them off on the home page.
//         return <Navigate to="/login" replace />;
//     }

//     return children;
// };

// Option 2: Using Outlet for nested routes (common practice)
const ProtectedRoute = () => {
    const { isAuthenticated, isLoading } = useContext(AuthContext);

    if (isLoading) {
        // Optional: Show a loading indicator while checking auth
        // Important to prevent flickering redirect before auth check completes
        return <div>Loading authentication...</div>; // Or a proper spinner
    }

    // If authenticated, render the child routes defined within this route
    // If not authenticated, redirect to the login page
    return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
};


export default ProtectedRoute;