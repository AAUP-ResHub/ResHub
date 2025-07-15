/**
 * UI Component Integration Tests for ResHub Chatbot
 * 
 * Tests the integration between UI components and the underlying services.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { App } from '../../../app/static/js/components/ui/App.js';
import { SessionList } from '../../../app/static/js/components/ui/SessionList.js';
import { ChatInput } from '../../../app/static/js/components/ui/ChatInput.js';
import { MessageList } from '../../../app/static/js/components/ui/MessageList.js';
import { ChatHistory } from '../../../app/static/js/components/ui/ChatHistory.js';
import { chatStore } from '../../../app/static/js/components/store/chatStore.js';
import * as apiService from '../../../app/static/js/components/services/apiService.js';
import * as SessionManager from '../../../app/static/js/components/services/SessionManager.js';
import { FeatureFlags } from '../../../app/static/js/components/services/featureFlags.js';

// Mock API responses
vi.mock('../../../app/static/js/components/services/apiService.js', () => ({
  fetchChatSessions: vi.fn(() => Promise.resolve([
    { session_id: 'session-1', title: 'Session 1', created_at: '2025-07-12T12:00:00Z' },
    { session_id: 'session-2', title: 'Session 2', created_at: '2025-07-12T13:00:00Z' }
  ])),
  
  fetchChatHistory: vi.fn(() => Promise.resolve({
    history: [
      { chat_id: 'chat-1', created_at: '2025-07-12T12:30:00Z', query: 'Test question 1' },
      { chat_id: 'chat-2', created_at: '2025-07-12T12:45:00Z', query: 'Test question 2' }
    ]
  })),
  
  getChatDetails: vi.fn(() => Promise.resolve({
    question: 'Test question',
    answer: 'Test answer',
    citations: '<citations>Citation 1</citations>'
  })),
  
  sendChatMessage: vi.fn((message) => Promise.resolve({
    session_id: 'session-1',
    answer: `Response to: ${message}`,
    citations: '<citations>Test citation</citations>'
  })),
  
  switchChatSession: vi.fn(() => Promise.resolve({ success: true })),
  createChatSession: vi.fn(() => Promise.resolve({ session_id: 'new-session', title: 'New Session' }))
}));

// Mock Feature Flags
vi.mock('../../../app/static/js/components/services/featureFlags.js', () => ({
  isFeatureEnabled: vi.fn((flag) => true),
  loadFeatureFlags: vi.fn(() => Promise.resolve({
    USE_NEW_CHATBOT_UI: true,
    USE_COMPONENT_API_SERVICE: true,
    USE_COMPONENT_STORE: true
  })),
  FeatureFlags: {
    initialize: vi.fn(),
    isEnabled: vi.fn(() => true)
  }
}));

describe('ChatBot UI Component Integration', () => {
  let container;
  
  beforeEach(() => {
    // Set up DOM container
    container = document.createElement('div');
    document.body.appendChild(container);
    
    // Reset chatStore
    chatStore.reset();
    
    // Clear mocks
    vi.clearAllMocks();
  });
  
  afterEach(() => {
    // Clean up
    container.remove();
  });
  
  describe('App Component Integration', () => {
    it('should initialize and render all components', async () => {
      // Create App component
      const app = App();
      container.appendChild(app);
      
      // Verify all components were rendered
      expect(container.querySelector('.chatbot-app')).not.toBeNull();
      expect(container.querySelector('.session-list-container')).not.toBeNull();
      expect(container.querySelector('.message-list-container')).not.toBeNull();
      expect(container.querySelector('.chat-form')).not.toBeNull();
      
      // Verify API initialization calls
      expect(apiService.fetchChatSessions).toHaveBeenCalled();
    });
  });
  
  describe('SessionList Component Integration', () => {
    it('should render sessions and handle session switching', async () => {
      // Set up sessions in store
      chatStore.setSessions([
        { session_id: 'test-1', title: 'Test Session 1' },
        { session_id: 'test-2', title: 'Test Session 2' }
      ]);
      
      // Create component
      const sessionList = SessionList();
      container.appendChild(sessionList);
      
      // Verify sessions are rendered
      expect(container.querySelectorAll('.session-item').length).toBe(2);
      
      // Simulate session click
      const secondSession = container.querySelectorAll('.session-item')[1];
      secondSession.click();
      
      // Verify API call was made
      expect(apiService.switchChatSession).toHaveBeenCalledWith('test-2');
    });
    
    it('should handle new session creation', async () => {
      // Create component
      const sessionList = SessionList();
      container.appendChild(sessionList);
      
      // Click new session button
      const newButton = container.querySelector('.new-session-btn');
      newButton.click();
      
      // Verify API call
      expect(apiService.createChatSession).toHaveBeenCalled();
    });
  });
  
  describe('ChatInput Component Integration', () => {
    it('should send message and update store on form submission', async () => {
      // Create component
      const chatInput = ChatInput();
      container.appendChild(chatInput);
      
      // Set input value and submit form
      const input = container.querySelector('#new-prompt');
      input.value = 'Test message';
      
      // Submit the form
      const form = container.querySelector('form');
      form.dispatchEvent(new Event('submit'));
      
      // Verify API call
      expect(apiService.sendChatMessage).toHaveBeenCalledWith('Test message', undefined);
      
      // Wait for promises to resolve
      await vi.waitFor(() => {
        // Verify message was added to store
        const state = chatStore.getState();
        expect(state.messages.length).toBeGreaterThan(0);
      });
    });
  });
  
  describe('MessageList Component Integration', () => {
    it('should render messages from the store', async () => {
      // Add messages to store
      chatStore.addMessage({ role: 'user', content: 'User question' });
      chatStore.addMessage({ 
        role: 'assistant', 
        content: 'AI response', 
        citations: '<citation id="1">Citation text</citation>' 
      });
      
      // Create component
      const messageList = MessageList();
      container.appendChild(messageList);
      
      // Verify messages are rendered
      const messages = container.querySelectorAll('.message-item');
      expect(messages.length).toBe(2);
      expect(messages[0].textContent).toContain('User question');
      expect(messages[1].textContent).toContain('AI response');
      
      // Verify citation is rendered
      expect(container.querySelector('.citation')).not.toBeNull();
    });
  });
  
  describe('ChatHistory Component Integration', () => {
    it('should render chat history and handle history item clicks', async () => {
      // Set up history in store
      chatStore.setChatHistory([
        { chat_id: 'chat-1', query: 'History question 1', timestamp: '2025-07-12T12:00:00Z' },
        { chat_id: 'chat-2', query: 'History question 2', timestamp: '2025-07-12T13:00:00Z' }
      ]);
      
      // Create component
      const chatHistory = ChatHistory();
      container.appendChild(chatHistory);
      
      // Verify history items are rendered
      const historyItems = container.querySelectorAll('.history-item');
      expect(historyItems.length).toBe(2);
      expect(historyItems[0].textContent).toContain('History question 1');
      
      // Simulate history item click
      historyItems[0].click();
      
      // Verify API call
      expect(apiService.getChatDetails).toHaveBeenCalledWith('chat-1');
    });
  });
});
