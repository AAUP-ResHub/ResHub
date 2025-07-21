/**
 * Chat Store for ResHub Chatbot
 * 
 * Single source of truth for application state.
 * Implements Publish/Subscribe pattern for reactive updates.
 */

class ChatStore {
  constructor() {
    this.state = {
      messages: [],
      chatHistory: [],
      sessions: [],
      currentSessionId: null,
      currentChatId: null,
      isLoading: false,
      error: null,
      user: null,
      featureFlags: {}
    };
    
    this.subscribers = new Map();
    this.nextSubscriberId = 1;
  }

  /**
   * Subscribe to state changes
   * @param {Function} callback - Function to call when state changes
   * @param {string|Array} keys - Specific state keys to watch (optional)
   * @returns {Function} Unsubscribe function
   */
  subscribe(callback, keys = null) {
    const id = this.nextSubscriberId++;
    
    this.subscribers.set(id, {
      callback,
      keys: Array.isArray(keys) ? keys : (keys ? [keys] : null)
    });

    // Return unsubscribe function
    return () => this.unsubscribe(id);
  }

  /**
   * Unsubscribe from state changes
   * @param {number} subscriberId - Subscriber ID
   */
  unsubscribe(subscriberId) {
    this.subscribers.delete(subscriberId);
  }

  /**
   * Notify subscribers of state changes
   * @param {Array} changedKeys - Keys that changed
   */
  notify(changedKeys = []) {
    this.subscribers.forEach(({ callback, keys }) => {
      // If subscriber has specific keys, only notify if those keys changed
      if (keys && keys.length > 0) {
        const shouldNotify = keys.some(key => changedKeys.includes(key));
        if (shouldNotify) {
          callback(this.state, changedKeys);
        }
      } else {
        // No specific keys, notify of all changes
        callback(this.state, changedKeys);
      }
    });
  }

  /**
   * Get current state
   * @returns {Object} Current state
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Add a message to the current conversation
   * @param {Object} message - Message object
   */
  addMessage(message) {
    this.state.messages = [...this.state.messages, message];
    this.notify(['messages']);
  }

  /**
   * Set chat history
   * @param {Array} history - Array of chat messages
   */
  setHistory(history) {
    this.state.chatHistory = [...history];
    this.state.messages = [...history]; // Also update current messages
    this.notify(['chatHistory', 'messages']);
  }

  /**
   * Set loading state
   * @param {boolean} isLoading - Loading state
   */
  setLoading(isLoading) {
    this.state.isLoading = Boolean(isLoading);
    this.notify(['isLoading']);
  }

  /**
   * Set error state
   * @param {string|Error|null} error - Error message or object
   */
  setError(error) {
    this.state.error = error;
    this.notify(['error']);
  }

  /**
   * Clear error state
   */
  clearError() {
    this.setError(null);
  }

  /**
   * Set sessions list
   * @param {Array} sessions - Array of session objects
   */
  setSessions(sessions) {
    this.state.sessions = [...sessions];
    this.notify(['sessions']);
  }

  /**
   * Set current session ID
   * @param {string|null} sessionId - Session ID
   */
  setCurrentSessionId(sessionId) {
    this.state.currentSessionId = sessionId;
    this.notify(['currentSessionId']);
  }

  /**
   * Batch update sessions and current session ID atomically
   * @param {Array} sessions - Sessions array
   * @param {string} currentSessionId - Current session ID
   */
  setSessionsAndCurrentId(sessions, currentSessionId) {
    this.state.sessions = sessions || [];
    this.state.currentSessionId = currentSessionId;
    // Single notification for both updates to ensure atomicity
    this.notify(['sessions', 'currentSessionId']);
  }

  /**
   * Set current chat ID
   * @param {string|null} chatId - Chat ID
   */
  setCurrentChatId(chatId) {
    this.state.currentChatId = chatId;
    this.notify(['currentChatId']);
  }

  /**
   * Clear all messages
   */
  clearMessages() {
    this.state.messages = [];
    this.state.chatHistory = [];
    this.notify(['messages', 'chatHistory']);
  }

  /**
   * Update a specific message
   * @param {string} messageId - Message ID
   * @param {Object} updates - Updates to apply
   */
  updateMessage(messageId, updates) {
    this.state.messages = this.state.messages.map(msg => 
      msg.id === messageId ? { ...msg, ...updates } : msg
    );
    this.notify(['messages']);
  }

  /**
   * Remove a message
   * @param {string} messageId - Message ID
   */
  removeMessage(messageId) {
    this.state.messages = this.state.messages.filter(msg => msg.id !== messageId);
    this.notify(['messages']);
  }

  /**
   * Set user information
   * @param {Object} user - User object
   */
  setUser(user) {
    this.state.user = user;
    this.notify(['user']);
  }

  /**
   * Get messages for current session
   * @returns {Array} Array of messages
   */
  getMessages() {
    return [...this.state.messages];
  }

  /**
   * Get sessions list
   * @returns {Array} Array of sessions
   */
  getSessions() {
    return [...this.state.sessions];
  }

  /**
   * Get current session
   * @returns {Object|null} Current session object
   */
  getCurrentSession() {
    if (!this.state.currentSessionId) return null;
    return this.state.sessions.find(s => s.session_id === this.state.currentSessionId) || null;
  }

  /**
   * Check if currently loading
   * @returns {boolean} Loading state
   */
  isLoading() {
    return this.state.isLoading;
  }

  /**
   * Get current error
   * @returns {string|Error|null} Current error
   */
  getError() {
    return this.state.error;
  }

  /**
   * Reset store to initial state (CRITICAL: Named resetState for test compatibility)
   */
  resetState() {
    this.state = {
      messages: [],
      chatHistory: [],
      sessions: [],
      currentSessionId: null,
      currentChatId: null,
      isLoading: false,
      error: null,
      user: null,
      featureFlags: {}
    };
    
    // Clear all subscribers
    this.subscribers.clear();
    this.nextSubscriberId = 1;
    
    this.notify(['messages', 'chatHistory', 'sessions', 'currentSessionId', 'currentChatId', 'isLoading', 'error', 'user', 'featureFlags']);
  }

  /**
   * Alias for resetState (for backward compatibility)
   */
  reset() {
    this.resetState();
  }

  /**
   * Batch update multiple state properties
   * @param {Object} updates - Object with state updates
   */
  batchUpdate(updates) {
    const changedKeys = [];
    
    Object.keys(updates).forEach(key => {
      if (this.state.hasOwnProperty(key)) {
        this.state[key] = updates[key];
        changedKeys.push(key);
      }
    });
    
    if (changedKeys.length > 0) {
      this.notify(changedKeys);
    }
  }

  /**
   * Debug method to log current state
   */
  debug() {
    console.log('ChatStore State:', {
      ...this.state,
      subscribersCount: this.subscribers.size
    });
  }
}

// Create and export singleton instance
export const chatStore = new ChatStore();

// Export class for testing
export { ChatStore };

export default chatStore;
