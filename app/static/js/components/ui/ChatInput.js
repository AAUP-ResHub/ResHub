/**
 * ChatInput Component for ResHub Chatbot
 * 
 * Handles user input, form submission, and integrates with chatStore.
 * Supports Enter key submission and prevents sending empty messages.
 */

import { chatStore } from '../store/chatStore.js';
import * as apiService from '../services/apiService.js';
import { parse as parseResponse } from '../services/responseParser.js';
import { SessionManager } from '../services/SessionManager.js';

/**
 * Create ChatInput component
 * @param {HTMLElement} container - Container element to render into
 * @returns {Object} Component instance with methods
 */
export function ChatInput(container) {
  if (!container) {
    throw new Error('ChatInput requires a container element');
  }

  let unsubscribe = null;
  let isSubmitting = false;

  // Create the input form
  const form = document.createElement('form');
  form.className = 'chat-input-form';
  form.noValidate = true;

  const inputGroup = document.createElement('div');
  inputGroup.className = 'input-group';

  // Create text input
  const textInput = document.createElement('textarea');
  textInput.className = 'form-control';
  textInput.placeholder = 'Ask me anything about research papers...';
  textInput.rows = 1;
  textInput.style.cssText = `
    resize: none;
    min-height: 44px;
    max-height: 120px;
  `;

  // Create submit button
  const submitButton = document.createElement('button');
  submitButton.type = 'submit';
  submitButton.className = 'btn btn-primary';
  submitButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
  submitButton.disabled = true;

  // Add elements to form
  inputGroup.appendChild(textInput);
  inputGroup.appendChild(submitButton);
  form.appendChild(inputGroup);
  container.appendChild(form);

  /**
   * Auto-resize textarea based on content
   */
  function autoResize() {
    textInput.style.height = 'auto';
    textInput.style.height = Math.min(textInput.scrollHeight, 120) + 'px';
  }

  /**
   * Update submit button state
   */
  function updateSubmitButton() {
    const hasText = textInput.value.trim().length > 0;
    const state = chatStore.getState();
    
    submitButton.disabled = !hasText || state.isLoading || isSubmitting;
    
    if (state.isLoading || isSubmitting) {
      submitButton.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div>';
    } else {
      submitButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
    }
  }

  /**
   * Send message to API and handle response
   */
  async function sendMessage(message) {
    if (isSubmitting || !message.trim()) {
      return;
    }

    isSubmitting = true;
    updateSubmitButton();

    try {
      // Add user message to store
      const userMessage = {
        id: Date.now() + '_user',
        type: 'user',
        content: message,
        prompt: message,
        timestamp: new Date().toISOString()
      };
      
      chatStore.addMessage(userMessage);
      chatStore.setLoading(true);
      
      // Clear input immediately after adding user message
      textInput.value = '';
      autoResize();
      updateSubmitButton();

      // Get current session using store method
      let currentSession = chatStore.getCurrentSession();
      const state = chatStore.getState();
      
      console.log(`[ChatInput] DEBUG: Current session from store:`, currentSession);
      console.log(`[ChatInput] DEBUG: Current session ID:`, state.currentSessionId);
      console.log(`[ChatInput] DEBUG: Store has ${state.sessions?.length || 0} total sessions`);
      
      // Ensure we have a valid session
      if (!currentSession || !currentSession.session_id) {
        console.log('[ChatInput] No current session, creating new one');
        
        // Get session directly from createSession to avoid race conditions
        // Don't clear messages - user may have existing messages visible
        const newSession = await SessionManager.createSession('', false);
        currentSession = newSession;
        
        console.log('[ChatInput] Created new session:', currentSession);
        
        // Validate session was created properly
        if (!currentSession || !currentSession.session_id) {
          console.error('[ChatInput] SessionManager.createSession() returned invalid session:', currentSession);
          throw new Error('Failed to create new session - createSession returned invalid data');
        }
      } else {
        console.log(`[ChatInput] Using existing session: ${currentSession.session_id}`);
      }

      // Send to API with session ID
      let response;
      try {
        response = await apiService.sendMessage(message, currentSession.session_id);
      } catch (error) {
        // If backend can't find session (404 error), create a new one and retry
        if (error.message && error.message.includes('404')) {
          console.log('[ChatInput] Backend session not found, creating new session and retrying');
          const newSession = await SessionManager.createSession('', false); // Don't clear messages
          currentSession = newSession;
          response = await apiService.sendMessage(message, currentSession.session_id);
        } else {
          throw error; // Re-throw other errors
        }
      }

      if (response.answer) {
        // Parse the AI response from direct backend format
        // Backend returns structured data directly, so we can use it as-is
        let citations = response.citations || [];
        
        // If citations is a string, try to parse it
        if (typeof citations === 'string' && citations.trim()) {
          try {
            // Try JSON parsing first
            citations = JSON.parse(citations);
          } catch (e) {
            // If not JSON, treat as plain text and create a simple citation array
            citations = [{ content: citations }];
          }
        }
        
        const parsedResponse = {
          answer: response.answer || '',
          citations: Array.isArray(citations) ? citations : [],
          extras: response.extras || ''
        };
        
        // Create AI message
        const aiMessage = {
          id: response.chat_id || Date.now() + '_ai',
          type: 'ai',
          content: parsedResponse.answer,
          answer: parsedResponse.answer,
          response: parsedResponse.answer,
          citations: parsedResponse.citations,
          extras: parsedResponse.extras,
          timestamp: new Date().toISOString(),
          session_id: response.session_id
        };
        
        chatStore.addMessage(aiMessage);

        // Update session title with first question if it's a new session
        // Use the session_id from the actual API response to ensure consistency
        const actualSessionId = response.session_id || currentSession.session_id;
        if (actualSessionId) {
          // Update session title (this will only update if title is 'New Session')
          await SessionManager.updateSessionTitle(actualSessionId, message);
          // Update session activity since this is a new message
          SessionManager.updateSessionActivity(actualSessionId);
          
          // CRITICAL: Ensure current session remains set for next question
          // Update currentSession object to match the actual session_id from backend
          if (actualSessionId !== currentSession.session_id) {
            console.log(`[ChatInput] Backend session ID differs: ${actualSessionId} vs ${currentSession.session_id}`);
            currentSession.session_id = actualSessionId;
          }
          
          // Make sure store knows about current session for next question
          chatStore.setCurrentSessionId(actualSessionId);
          console.log(`[ChatInput] Current session confirmed: ${actualSessionId}`);
        }
        
      } else if (response.error) {
        // Handle API error
        const errorMessage = response.error;
        chatStore.setError(errorMessage);
        
        // Add error message to chat
        const errorMsg = {
          id: Date.now() + '_error',
          type: 'ai',
          content: `I apologize, but I encountered an error: ${errorMessage}`,
          answer: `I apologize, but I encountered an error: ${errorMessage}`,
          timestamp: new Date().toISOString()
        };
        
        chatStore.addMessage(errorMsg);
      } else {
        // Handle unexpected response format
        console.warn('Unexpected response format:', response);
        const errorMessage = 'Received unexpected response format from server';
        chatStore.setError(errorMessage);
        
        const errorMsg = {
          id: Date.now() + '_error',
          type: 'ai',
          content: `I apologize, but I received an unexpected response: ${errorMessage}`,
          answer: `I apologize, but I received an unexpected response: ${errorMessage}`,
          timestamp: new Date().toISOString()
        };
        
        chatStore.addMessage(errorMsg);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      chatStore.setError(error.message || 'Network error occurred');
      
      // Add error message to chat
      const errorMsg = {
        id: Date.now() + '_error',
        type: 'ai',
        content: 'I apologize, but I encountered a network error. Please check your connection and try again.',
        answer: 'I apologize, but I encountered a network error. Please check your connection and try again.',
        timestamp: new Date().toISOString()
      };
      
      chatStore.addMessage(errorMsg);
      
    } finally {
      chatStore.setLoading(false);
      isSubmitting = false;
      updateSubmitButton();
      textInput.focus();
    }
  }

  /**
   * Handle form submission
   */
  function handleSubmit(e) {
    e.preventDefault();
    
    const message = textInput.value.trim();
    if (message && !isSubmitting) {
      sendMessage(message);
    }
  }

  /**
   * Handle key press (Enter to submit)
   */
  function handleKeyPress(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  /**
   * Handle input changes
   */
  function handleInput() {
    autoResize();
    updateSubmitButton();
  }

  /**
   * Handle state changes from store
   */
  function handleStateChange(state, changedKeys) {
    if (changedKeys.includes('isLoading') || changedKeys.includes('error')) {
      updateSubmitButton();
    }
  }

  /**
   * Initialize component
   */
  function initialize() {
    // Add event listeners
    form.addEventListener('submit', handleSubmit);
    textInput.addEventListener('keypress', handleKeyPress);
    textInput.addEventListener('input', handleInput);
    textInput.addEventListener('paste', () => setTimeout(autoResize, 0));

    // Subscribe to store changes
    unsubscribe = chatStore.subscribe(handleStateChange, ['isLoading', 'error']);

    // Initial state
    updateSubmitButton();
    textInput.focus();

    console.log('ChatInput component initialized');
  }

  /**
   * Destroy component
   */
  function destroy() {
    if (unsubscribe) {
      unsubscribe();
      unsubscribe = null;
    }

    // Remove event listeners
    form.removeEventListener('submit', handleSubmit);
    textInput.removeEventListener('keypress', handleKeyPress);
    textInput.removeEventListener('input', handleInput);

    // Clear container
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }

    console.log('ChatInput component destroyed');
  }

  /**
   * Focus the input
   */
  function focus() {
    textInput.focus();
  }

  /**
   * Clear the input
   */
  function clear() {
    textInput.value = '';
    autoResize();
    updateSubmitButton();
  }

  /**
   * Set input value
   */
  function setValue(value) {
    textInput.value = value || '';
    autoResize();
    updateSubmitButton();
  }

  /**
   * Get input value
   */
  function getValue() {
    return textInput.value;
  }

  // Initialize component
  initialize();

  // Return component API
  return {
    destroy,
    focus,
    clear,
    setValue,
    getValue,
    element: form
  };
}

export default ChatInput;
