/**
 * api.js - Centralized fetch handler for VendorBridge Backend
 */

const API_BASE_URL = 'http://localhost:5000/api';

/**
 * Perform an authenticated fetch request
 * @param {string} endpoint - The API endpoint (e.g. '/auth/login')
 * @param {object} options - Fetch options (method, body, etc)
 */
async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem('vb-token');
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
        const data = await response.json();
        
        if (!response.ok) {
            // Only trigger session expiration for endpoints other than login
            if (endpoint !== '/auth/login' && (response.status === 401 || (response.status === 404 && data.error === 'User not found'))) {
                clearAuthData();
                if (window.location.pathname.indexOf('login.html') === -1) {
                    window.location.href = 'login.html';
                }
                throw new Error('Session expired or not logged in. Please log in.');
            }
            throw new Error(data.error || data.msg || 'API Request Failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Authentication Helpers
function setAuthData(token, user) {
    localStorage.setItem('vb-token', token);
    localStorage.setItem('vb-user', JSON.stringify(user));
}

function clearAuthData() {
    localStorage.removeItem('vb-token');
    localStorage.removeItem('vb-user');
}

function getUser() {
    const userStr = localStorage.getItem('vb-user');
    return userStr ? JSON.parse(userStr) : null;
}
