/**
 * API Service for ResHub Chatbot
 * 
 * Centralizes all fetch calls to the Flask backend.
 * Handles JSON parsing and basic error handling.
 */

// API endpoint URLs
const API_ENDPOINTS = {
  CHAT: '/chatbot/api/chat',
  SESSIONS: '/chatbot/api/chat/sessions',
  HISTORY: '/chatbot/api/chat/history',
  CHAT_DETAILS: '/chatbot/api/chat/details',
  FEEDBACK: '/chatbot/api/feedback',
  FEATURE_FLAGS: '/api/feature-flags'
};

/**
 * Get CSRF token from meta tag
 */
function getCSRFToken() {
  const token = document.querySelector('meta[name="csrf-token"]');
  return token ? token.getAttribute('content') : '';
}

/**
 * Make authenticated API request with CSRF protection
 */
async function apiRequest(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
      ...options.headers
    },
    credentials: 'same-origin'
  };

  const response = await fetch(url, { ...defaultOptions, ...options });
  
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

/**
 * Send a chat message
 * @param {string} prompt - User message
 * @param {string} sessionId - Current session ID
 * @param {Object} options - Additional options (years, style, etc.)
 * @returns {Promise<Object>} API response
 */
export async function sendMessage(prompt, sessionId, options = {}) {
  const payload = {
    prompt,
    session_id: sessionId,
    years: options.years || null,
    style: options.style || 'APA',
    ...options
  };

  return apiRequest(API_ENDPOINTS.CHAT, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Get chat history for a session
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} Chat history data
 */
export async function getChatHistory(sessionId) {
  const url = `${API_ENDPOINTS.HISTORY}?session_id=${encodeURIComponent(sessionId)}`;
  return apiRequest(url);
}

/**
 * Get all chat sessions for current user
 * @returns {Promise<Object>} Sessions data
 */
export async function getSessions() {
  return apiRequest(API_ENDPOINTS.SESSIONS);
}

/**
 * Get details of a specific chat interaction
 * @param {string} chatId - Chat ID
 * @returns {Promise<Object>} Chat details
 */
export async function getChatDetails(chatId) {
  const url = `${API_ENDPOINTS.CHAT_DETAILS}/${encodeURIComponent(chatId)}`;
  return apiRequest(url);
}

/**
 * Submit feedback for a chat interaction
 * @param {string} chatId - Chat ID
 * @param {number} rating - Thumbs up (1) or down (-1)
 * @param {string} feedback - Optional feedback text
 * @returns {Promise<Object>} Feedback response
 */
export async function submitFeedback(chatId, rating, feedback = '') {
  const payload = {
    chat_id: chatId,
    rating,
    feedback
  };

  return apiRequest(API_ENDPOINTS.FEEDBACK, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Get feature flags from backend
 * @returns {Promise<Object>} Feature flags object
 */
export async function getFeatureFlags() {
  try {
    return await apiRequest(API_ENDPOINTS.FEATURE_FLAGS);
  } catch (error) {
    console.warn('Failed to fetch feature flags, using defaults:', error);
    // Return default flags if API fails
    return {
      USE_NEW_CHATBOT_UI: false,
      ENABLE_ADVANCED_SEARCH: false,
      ENABLE_EXPORT_CHAT: false
    };
  }
}

/**
 * Create a new chat session
 * @param {string} title - Session title
 * @returns {Promise<Object>} New session data
 */
export async function createSession(title = '') {
  const payload = {
    title: title || `Chat session ${new Date().toLocaleString()}`
  };

  return apiRequest(API_ENDPOINTS.SESSIONS, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

/**
 * Update session title
 * @param {string} sessionId - Session ID
 * @param {string} title - New title
 * @returns {Promise<Object>} Updated session data
 */
export async function updateSessionTitle(sessionId, title) {
  const payload = { title };
  
  return apiRequest(`${API_ENDPOINTS.SESSIONS}/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export default {
  sendMessage,
  getChatHistory,
  getSessions,
  getChatDetails,
  submitFeedback,
  getFeatureFlags,
  createSession,
  updateSessionTitle
};
