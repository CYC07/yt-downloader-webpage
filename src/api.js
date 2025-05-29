// src/api.js
import axios from 'axios';

// Function to get a cookie value by name
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Configure axios instance
const apiClient = axios.create({
    baseURL: 'http://localhost:8000/api', // Your Django backend API URL
    withCredentials: true, // Crucial for sending/receiving session cookies
    headers: {
        'Content-Type': 'application/json',
    }
});

// --- ADD THIS INTERCEPTOR ---
// Add an interceptor to automatically include the CSRF token
apiClient.interceptors.request.use(config => {
    // Only add the CSRF token for methods that require it (Django default: not GET, HEAD, OPTIONS, TRACE)
    // You could be more specific with: ['POST', 'PUT', 'DELETE', 'PATCH']
    if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(config.method.toUpperCase())) {
        const csrfToken = getCookie('csrftoken');
        if (csrfToken) {
            config.headers['X-CSRFToken'] = csrfToken;
            console.log('CSRF Token added to request headers:', csrfToken); // For debugging
        } else {
            console.warn('CSRF Token cookie not found.'); // For debugging
        }
    }
    return config;
}, error => {
    // Do something with request error
    return Promise.reject(error);
});
// --- END OF INTERCEPTOR ---


export default apiClient;