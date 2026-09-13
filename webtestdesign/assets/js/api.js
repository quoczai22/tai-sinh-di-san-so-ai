/**
 * API.JS - Xử lý gọi fetch/axios API
 */

const API_BASE_URL = 'http://localhost:5000/api';

/**
 * Hàm gọi API chung
 * @param {string} endpoint 
 * @param {object} options 
 * @returns {Promise<any>}
 */
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Fetch API error:', error);
        throw error;
    }
}
