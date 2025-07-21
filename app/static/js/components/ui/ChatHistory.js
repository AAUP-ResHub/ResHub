/**
 * ChatHistory Component for ResHub Chatbot
 * 
 * Combines SessionList and MessageList into a unified chat history interface.
 * Provides session management and message display functionality.
 */

import { SessionList } from './SessionList.js';
import { MessageList } from './MessageList.js';
import { chatStore } from '../store/chatStore.js';

/**
 * Create ChatHistory component
 * @param {HTMLElement} container - Container element to render into
 * @param {Object} options - Configuration options
 * @returns {Object} Component instance with methods
 */
export function ChatHistory(container, options = {}) {
  if (!container) {
    throw new Error('ChatHistory requires a container element');
  }

  const {
    showSessions = true,
    showMessages = true,
    layout = 'horizontal' // 'horizontal' | 'vertical'
  } = options;

  let unsubscribe = null;
  let sessionListComponent = null;
  let messageListComponent = null;

  // Create main layout container
  const historyContainer = document.createElement('div');
  historyContainer.className = 'chat-history-container';

  // Create sessions section
  let sessionsSection = null;
  if (showSessions) {
    sessionsSection = document.createElement('div');
    sessionsSection.className = layout === 'horizontal' 
      ? 'sessions-section col-md-4 pe-3' 
      : 'sessions-section mb-3';
    
    const sessionsCard = document.createElement('div');
    sessionsCard.className = 'card h-100';
    
    const sessionsCardBody = document.createElement('div');
    sessionsCardBody.className = 'card-body';
    
    sessionsCard.appendChild(sessionsCardBody);
    sessionsSection.appendChild(sessionsCard);
    
    // Initialize SessionList component
    sessionListComponent = SessionList(sessionsCardBody);
  }

  // Create messages section
  let messagesSection = null;
  if (showMessages) {
    messagesSection = document.createElement('div');
    messagesSection.className = layout === 'horizontal' 
      ? 'messages-section col-md-8' 
      : 'messages-section';
    
    const messagesCard = document.createElement('div');
    messagesCard.className = 'card h-100';
    
    const messagesCardHeader = document.createElement('div');
    messagesCardHeader.className = 'card-header d-flex justify-content-between align-items-center';
    
    const messagesTitle = document.createElement('h6');
    messagesTitle.className = 'mb-0';
    messagesTitle.textContent = 'Chat History';
    
    const clearButton = document.createElement('button');
    clearButton.type = 'button';
    clearButton.className = 'btn btn-sm btn-outline-danger';
    clearButton.innerHTML = '<i class="fas fa-trash"></i> Clear';
    clearButton.title = 'Clear current session messages';
    
    messagesCardHeader.appendChild(messagesTitle);
    messagesCardHeader.appendChild(clearButton);
    
    const messagesCardBody = document.createElement('div');
    messagesCardBody.className = 'card-body p-0';
    
    messagesCard.appendChild(messagesCardHeader);
    messagesCard.appendChild(messagesCardBody);
    messagesSection.appendChild(messagesCard);
    
    // Initialize MessageList component
    messageListComponent = MessageList(messagesCardBody);
    
    // Add clear button handler
    clearButton.addEventListener('click', handleClearMessages);
  }

  // Set up layout
  if (layout === 'horizontal') {
    historyContainer.className += ' row';
  }

  // Add sections to container
  if (sessionsSection) historyContainer.appendChild(sessionsSection);
  if (messagesSection) historyContainer.appendChild(messagesSection);
  
  container.appendChild(historyContainer);

  /**
   * Handle clear messages button click
   */
  function handleClearMessages() {
    if (confirm('Are you sure you want to clear all messages in the current session?')) {
      chatStore.clearMessages();
    }
  }

  /**
   * Update messages title based on current session
   */
  function updateMessagesTitle() {
    if (!messagesSection) return;
    
    const state = chatStore.getState();
    const titleElement = messagesSection.querySelector('h6');
    
    if (titleElement) {
      if (state.currentSession?.title) {
        titleElement.textContent = state.currentSession.title;
      } else {
        titleElement.textContent = 'Chat History';
      }
    }
  }

  /**
   * Handle state changes from store
   */
  function handleStateChange(state, changedKeys) {
    if (changedKeys.includes('currentSession')) {
      updateMessagesTitle();
    }
  }

  /**
   * Initialize component
   */
  function initialize() {
    // Subscribe to store changes
    unsubscribe = chatStore.subscribe(handleStateChange, ['currentSession']);
    
    // Initial update
    updateMessagesTitle();
    
    console.log('ChatHistory component initialized');
  }

  /**
   * Destroy component
   */
  function destroy() {
    if (unsubscribe) {
      unsubscribe();
      unsubscribe = null;
    }
    
    // Destroy child components
    if (sessionListComponent) {
      sessionListComponent.destroy();
      sessionListComponent = null;
    }
    
    if (messageListComponent) {
      messageListComponent.destroy();
      messageListComponent = null;
    }
    
    // Clear container
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    
    console.log('ChatHistory component destroyed');
  }

  /**
   * Refresh all data
   */
  function refresh() {
    if (sessionListComponent) {
      sessionListComponent.refresh();
    }
    
    if (messageListComponent) {
      messageListComponent.refresh();
    }
  }

  /**
   * Scroll messages to bottom
   */
  function scrollToBottom() {
    if (messageListComponent) {
      messageListComponent.scrollToBottom();
    }
  }

  /**
   * Add a message (convenience method)
   */
  function addMessage(message) {
    if (messageListComponent) {
      messageListComponent.addMessage(message);
    }
  }

  /**
   * Clear messages (convenience method)
   */
  function clearMessages() {
    if (messageListComponent) {
      messageListComponent.clearMessages();
    }
  }

  /**
   * Get current session info
   */
  function getCurrentSession() {
    return chatStore.getState().currentSession;
  }

  /**
   * Get all messages
   */
  function getMessages() {
    return chatStore.getState().messages;
  }

  /**
   * Show/hide sessions panel
   */
  function toggleSessions(show) {
    if (sessionsSection) {
      sessionsSection.style.display = show ? 'block' : 'none';
      
      // Adjust messages section width if horizontal layout
      if (layout === 'horizontal' && messagesSection) {
        messagesSection.className = show 
          ? 'messages-section col-md-8'
          : 'messages-section col-md-12';
      }
    }
  }

  /**
   * Show/hide messages panel
   */
  function toggleMessages(show) {
    if (messagesSection) {
      messagesSection.style.display = show ? 'block' : 'none';
      
      // Adjust sessions section width if horizontal layout
      if (layout === 'horizontal' && sessionsSection) {
        sessionsSection.className = show 
          ? 'sessions-section col-md-4 pe-3'
          : 'sessions-section col-md-12';
      }
    }
  }

  // Initialize component
  initialize();

  // Return component API
  return {
    destroy,
    refresh,
    scrollToBottom,
    addMessage,
    clearMessages,
    getCurrentSession,
    getMessages,
    toggleSessions,
    toggleMessages,
    element: historyContainer,
    sessionList: sessionListComponent,
    messageList: messageListComponent
  };
}

export default ChatHistory;
