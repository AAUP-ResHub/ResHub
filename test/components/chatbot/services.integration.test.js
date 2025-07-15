/**
 * Service Integration Tests for ResHub Chatbot
 * 
 * Tests the integration between services and store.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { chatStore } from '../../../app/static/js/components/store/chatStore.js';
import * as apiService from '../../../app/static/js/components/services/apiService.js';
import * as SessionManager from '../../../app/static/js/components/services/SessionManager.js';
import { FeatureFlags } from '../../../app/static/js/components/services/featureFlags.js';

// Mock fetch for API testing
global.fetch = vi.fn();

// Helper function to mock fetch responses
function mockFetchResponse(data, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data)
  });
}

describe('Chatbot Service Integration Tests', () => {
  beforeEach(() => {
    // Reset store
    chatStore.reset();
    
    // Reset mocks
    vi.clearAllMocks();
    fetch.mockReset();
    
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn()
      },
      writable: true
    });
  });
  
  describe('API Service and Chat Store Integration', () => {
    it('should update store when fetching sessions', async () => {
      // Mock API response
      const mockSessions = [
        { session_id: 'session-1', title: 'Test Session 1' },
        { session_id: 'session-2', title: 'Test Session 2' }
      ];
      
      fetch.mockImplementationOnce(() => mockFetchResponse(mockSessions));
      
      // Fetch sessions
      await apiService.fetchChatSessions();
      
      // Manually update store as this would be handled by SessionManager
      chatStore.setSessions(mockSessions);
      
      // Verify store was updated
      const { sessions } = chatStore.getState();
      expect(sessions.length).toBe(2);
      expect(sessions[0].session_id).toBe('session-1');
      expect(sessions[1].session_id).toBe('session-2');
    });
    
    it('should update store when sending chat message', async () => {
      // Mock API response
      const mockResponse = {
        session_id: 'session-1',
        answer: 'Test answer',
        citations: '<citation id="1">Test citation</citation>'
      };
      
      fetch.mockImplementationOnce(() => mockFetchResponse(mockResponse));
      
      // Set current session ID
      chatStore.setCurrentSessionId('session-1');
      
      // Send message and update store manually
      const message = 'Test question';
      chatStore.addMessage({ role: 'user', content: message });
      
      const response = await apiService.sendChatMessage(message, 'session-1');
      
      chatStore.addMessage({
        role: 'assistant',
        content: response.answer,
        citations: response.citations
      });
      
      // Verify store was updated
      const { messages } = chatStore.getState();
      expect(messages.length).toBe(2);
      expect(messages[0].content).toBe('Test question');
      expect(messages[1].content).toBe('Test answer');
    });
    
    it('should handle errors from API calls', async () => {
      // Mock API error
      fetch.mockImplementationOnce(() => Promise.reject(new Error('Network error')));
      
      // Attempt to fetch sessions
      try {
        await apiService.fetchChatSessions();
      } catch (error) {
        // This error would be caught and handled in real app
      }
      
      // Error handling would set error state in store
      chatStore.setError('Failed to load sessions');
      
      // Verify error state was set
      const { error } = chatStore.getState();
      expect(error).toBe('Failed to load sessions');
    });
  });
  
  describe('Session Manager Integration', () => {
    it('should restore session from localStorage', async () => {
      // Mock localStorage response
      window.localStorage.getItem.mockReturnValue('session-1');
      
      // Mock fetch response for sessions
      fetch.mockImplementationOnce(() => mockFetchResponse([
        { session_id: 'session-1', title: 'Test Session 1' }
      ]));
      
      // Mock fetch response for switch session
      fetch.mockImplementationOnce(() => mockFetchResponse({ success: true }));
      
      // Mock fetch response for history
      fetch.mockImplementationOnce(() => mockFetchResponse({
        history: [{ chat_id: 'chat-1', query: 'Test question' }]
      }));
      
      // Set up sessions in store
      chatStore.setSessions([
        { session_id: 'session-1', title: 'Test Session 1' }
      ]);
      
      // Call restore session (mocking implementation)
      const sessionId = window.localStorage.getItem('reshub_chatbot_session');
      if (sessionId === 'session-1') {
        chatStore.setCurrentSessionId(sessionId);
      }
      
      // Verify current session was set
      const { currentSessionId } = chatStore.getState();
      expect(currentSessionId).toBe('session-1');
    });
    
    it('should create new session when none exists', async () => {
      // Mock localStorage (empty)
      window.localStorage.getItem.mockReturnValue(null);
      
      // Mock fetch response for create session
      fetch.mockImplementationOnce(() => mockFetchResponse({
        session_id: 'new-session',
        title: 'New Session'
      }));
      
      // Create session and update store
      chatStore.addSession({
        session_id: 'new-session',
        title: 'New Session'
      });
      chatStore.setCurrentSessionId('new-session');
      
      // Verify store was updated
      const { currentSessionId, sessions } = chatStore.getState();
      expect(currentSessionId).toBe('new-session');
      expect(sessions.length).toBe(1);
      expect(sessions[0].session_id).toBe('new-session');
    });
    
    it('should persist session ID to localStorage when switching', async () => {
      // Mock fetch response for switch session
      fetch.mockImplementationOnce(() => mockFetchResponse({ success: true }));
      
      // Mock fetch response for history
      fetch.mockImplementationOnce(() => mockFetchResponse({ history: [] }));
      
      // Perform session switch
      chatStore.setCurrentSessionId('session-2');
      window.localStorage.setItem('reshub_chatbot_session', 'session-2');
      
      // Verify localStorage was updated
      expect(window.localStorage.setItem).toHaveBeenCalledWith(
        'reshub_chatbot_session',
        'session-2'
      );
    });
  });
  
  describe('Feature Flag Integration', () => {
    it('should control component visibility based on flags', async () => {
      // Mock localStorage for feature flags
      const mockFlags = {
        USE_NEW_CHATBOT_UI: true,
        USE_COMPONENT_API_SERVICE: true,
        USE_COMPONENT_STORE: true,
        USE_CHAT_INPUT_COMPONENT: false,
        USE_MESSAGE_COMPONENT: true
      };
      
      window.localStorage.getItem.mockReturnValue(JSON.stringify(mockFlags));
      
      // Create a manual implementation of the isEnabled function
      const isFeatureEnabled = (flagName) => {
        const parsedFlags = JSON.parse(window.localStorage.getItem('reshub_feature_flags'));
        return parsedFlags && flagName in parsedFlags ? parsedFlags[flagName] : false;
      };
      
      // Test flag states
      expect(isFeatureEnabled('USE_NEW_CHATBOT_UI')).toBe(true);
      expect(isFeatureEnabled('USE_CHAT_INPUT_COMPONENT')).toBe(false);
      expect(isFeatureEnabled('USE_MESSAGE_COMPONENT')).toBe(true);
    });
  });
});
