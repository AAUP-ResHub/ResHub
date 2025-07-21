/**
 * Session Manager for ResHub Chatbot
 * 
 * Handles the logic for creating, switching, and managing chat sessions.
 * Interacts with localStorage for persistence and updates the central chatStore.
 */

import * as apiService from './apiService.js';

class SessionManagerService {
  constructor() {
    this.currentSessionId = null;
    this.sessions = [];
    this.chatStore = null; // Will be injected
  }

  /**
   * Initialize session manager with chat store
   * @param {Object} store - Chat store instance
   */
  initialize(store) {
    this.chatStore = store;
    this.loadFromLocalStorage();
  }

  /**
   * Load session data from localStorage
   */
  loadFromLocalStorage() {
    try {
      const savedSessionId = localStorage.getItem('currentSessionId');
      if (savedSessionId) {
        this.currentSessionId = savedSessionId;
        console.log('Restored session from localStorage:', savedSessionId);
      }

      const savedSessions = localStorage.getItem('chatSessions');
      if (savedSessions) {
        this.sessions = JSON.parse(savedSessions);
        console.log('Restored sessions from localStorage:', this.sessions.length);
      }
    } catch (error) {
      console.warn('Error loading from localStorage:', error);
    }
  }

  /**
   * Save session data to localStorage
   */
  saveToLocalStorage() {
    try {
      if (this.currentSessionId) {
        localStorage.setItem('currentSessionId', this.currentSessionId);
      }
      
      if (this.sessions.length > 0) {
        localStorage.setItem('chatSessions', JSON.stringify(this.sessions));
      }
    } catch (error) {
      console.warn('Error saving to localStorage:', error);
    }
  }

  /**
   * Get current session ID
   * @returns {string|null} Current session ID
   */
  getCurrentSessionId() {
    return this.currentSessionId;
  }

  /**
   * Set current session ID
   * @param {string} sessionId - Session ID to set as current
   */
  setCurrentSessionId(sessionId) {
    this.currentSessionId = sessionId;
    this.saveToLocalStorage();
    
    if (this.chatStore) {
      this.chatStore.setCurrentSessionId(sessionId);
    }
  }

  /**
   * Load all sessions from backend
   * @returns {Promise<Array>} Array of session objects
   */
  async loadSessions() {
    try {
      const response = await apiService.getSessions();
      this.sessions = response.sessions || [];
      this.saveToLocalStorage();
      
      if (this.chatStore) {
        this.chatStore.setSessions(this.sessions);
      }
      
      return this.sessions;
    } catch (error) {
      console.error('Error loading sessions:', error);
      throw error;
    }
  }

  /**
   * Create a new session
   * @param {string} title - Session title
   * @returns {Promise<Object>} New session object
   */
  async createSession(title = '', clearMessages = true) {
    try {
      // If no title provided, will be updated with first question later
      const sessionTitle = title || `New Session`;
      
      // Create session via API (this will create it in the backend)
      const response = await apiService.createSession(sessionTitle);
      
      if (response.session_id) {
        const newSession = {
          session_id: response.session_id,
          title: sessionTitle,
          created_at: new Date().toISOString(),
          last_active: new Date().toISOString(),
          is_active: true
        };

        // Add to local sessions array
        this.sessions.unshift(newSession);
        
        if (this.chatStore) {
          // ATOMIC UPDATE: Update both sessions and current session in single operation
          this.chatStore.setSessionsAndCurrentId(this.sessions, response.session_id);
          
          // Conditionally clear messages based on parameter
          if (clearMessages) {
            this.chatStore.setHistory([]);
            console.log(`[SessionManager] Created new session ${response.session_id} - messages cleared`);
          } else {
            console.log(`[SessionManager] Created new session ${response.session_id} - messages preserved`);
          }
          
          // Also update local reference
          this.currentSessionId = response.session_id;
          this.saveToLocalStorage();
        } else {
          console.error('[SessionManager] chatStore is null/undefined!');
          // Fallback: set session ID even without store
          this.currentSessionId = response.session_id;
          this.saveToLocalStorage();
        }
        
        return newSession;
      }
      
      throw new Error('Failed to create session: No session ID returned');
    } catch (error) {
      console.error('Error creating session:', error);
      throw error;
    }
  }

  /**
   * Switch to a different session
   * @param {string} sessionId - Session ID to switch to
   * @returns {Promise<void>}
   */
  async switchSession(sessionId) {
    try {
      if (sessionId === this.currentSessionId) {
        console.log('Already on session:', sessionId);
        return;
      }

      console.log(`[SessionManager] Switching from ${this.currentSessionId} to ${sessionId}`);
      
      if (this.chatStore) {
        this.chatStore.setLoading(true);
        // Don't clear messages until new ones are loaded
      }

      // Load chat history for the new session FIRST
      await this.loadChatHistory(sessionId);
      
      // Only after successful loading, update current session
      this.setCurrentSessionId(sessionId);
      
      // Don't update session activity timestamp on switch - only on new messages
      
      console.log(`[SessionManager] Successfully switched to session ${sessionId}`);
      
    } catch (error) {
      console.error('Error switching session:', error);
      // On error, restore previous session or clear messages
      if (this.chatStore) {
        this.chatStore.setHistory([]);
      }
      throw error;
    } finally {
      if (this.chatStore) {
        this.chatStore.setLoading(false);
      }
    }
  }

  /**
   * Load chat history for a session
   * @param {string} sessionId - Session ID
   * @returns {Promise<Array>} Array of chat messages
   */
  async loadChatHistory(sessionId) {
    try {
      console.log(`[SessionManager] Loading chat history for session ${sessionId}`);
      const response = await apiService.getChatHistory(sessionId);
      // Backend now returns properly formatted message pairs
      const messages = response.messages || response.chats || [];
      
      console.log(`[SessionManager] Loaded ${messages.length} messages for session ${sessionId}:`, messages.slice(0, 2));
      
      if (this.chatStore) {
        this.chatStore.setHistory(messages);
        console.log(`[SessionManager] Set history in store for session ${sessionId}`);
      }
      
      return messages;
    } catch (error) {
      console.error(`[SessionManager] Error loading chat history for session ${sessionId}:`, error);
      // Set empty messages on error to avoid confusion
      if (this.chatStore) {
        this.chatStore.setHistory([]);
      }
      // Don't throw error - just return empty array to continue session switch
      return [];
    }
  }

  /**
   * Update session activity timestamp
   * @param {string} sessionId - Session ID
   */
  updateSessionActivity(sessionId) {
    const session = this.sessions.find(s => s.session_id === sessionId);
    if (session) {
      session.last_active = new Date().toISOString();
      this.saveToLocalStorage();
      
      if (this.chatStore) {
        this.chatStore.setSessions(this.sessions);
      }
    }
  }

  /**
   * Get session by ID
   * @param {string} sessionId - Session ID
   * @returns {Object|null} Session object or null
   */
  getSession(sessionId) {
    return this.sessions.find(s => s.session_id === sessionId) || null;
  }

  /**
   * Get all sessions
   * @returns {Array} Array of session objects
   */
  getSessions() {
    return [...this.sessions];
  }

  /**
   * Clear all session data (for testing/reset)
   */
  clear() {
    this.currentSessionId = null;
    this.sessions = [];
    
    try {
      localStorage.removeItem('currentSessionId');
      localStorage.removeItem('chatSessions');
    } catch (error) {
      console.warn('Error clearing localStorage:', error);
    }
    
    if (this.chatStore) {
      this.chatStore.setCurrentSessionId(null);
      this.chatStore.setSessions([]);
      this.chatStore.clearMessages();
    }
  }

  /**
   * Update session title with first question
   * @param {string} sessionId - Session ID
   * @param {string} question - First question to use as title
   */
  async updateSessionTitle(sessionId, question) {
    // Find session in local array first
    let session = this.sessions.find(s => s.session_id === sessionId);
    
    // If not found locally, check if it exists in store and sync
    if (!session && this.chatStore) {
      const storeState = this.chatStore.getState();
      const storeSession = storeState.sessions?.find(s => s.session_id === sessionId);
      if (storeSession) {
        this.sessions.unshift(storeSession); // Add to local array
        session = storeSession;
        console.log(`[SessionManager] Synced session ${sessionId} from store`);
      }
    }
    
    if (session && session.title === 'New Session') {
      try {
        // Truncate long questions and use as title
        const truncatedTitle = question.length > 50 ? 
          question.substring(0, 47) + '...' : question;
        
        console.log(`[SessionManager] Updating session ${sessionId} title from "${session.title}" to "${truncatedTitle}"`);
        
        // Update backend first
        await apiService.updateSessionTitle(sessionId, truncatedTitle);
        
        // Update local session
        session.title = truncatedTitle;
        this.saveToLocalStorage();
        
        if (this.chatStore) {
          this.chatStore.setSessions(this.sessions);
        }
        
        console.log(`[SessionManager] Successfully updated session ${sessionId} title to: "${truncatedTitle}"`);
      } catch (error) {
        console.error(`[SessionManager] Failed to update session title:`, error);
      }
    } else if (!session) {
      console.warn(`[SessionManager] Session ${sessionId} not found for title update`);
    } else {
      console.log(`[SessionManager] Session ${sessionId} title is already set: "${session.title}"`);
    }
  }

  /**
   * Alias for switchSession (for backward compatibility)
   * @param {string} sessionId - Session ID to switch to
   * @returns {Promise<void>}
   */
  async switchToSession(sessionId) {
    return this.switchSession(sessionId);
  }
}

// Create singleton instance
export const SessionManager = new SessionManagerService();

// Export class for testing
export { SessionManagerService };

export default SessionManager;
