/**
 * App Component for ResHub Chatbot
 * 
 * Main application component that combines all UI components.
 * Handles initialization, layout, and high-level state management.
 */

import { ChatHistory } from './ChatHistory.js';
import { MessageList } from './MessageList.js';
import { ChatInput } from './ChatInput.js';
import { chatStore } from '../store/chatStore.js';
import { SessionManager } from '../services/SessionManager.js';
import { FeatureFlags } from '../services/featureFlags.js';

/**
 * Create App component
 * @param {HTMLElement} container - Container element to render into
 * @param {Object} options - Configuration options
 * @returns {Object} Component instance with methods
 */
export function App(container, options = {}) {
  if (!container) {
    throw new Error('App requires a container element');
  }

  const {
    showHistory = true,
    layout = 'vertical', // 'vertical' | 'horizontal'
    theme = 'light'
  } = options;

  let unsubscribe = null;
  let sessionManager = null;
  let chatHistoryComponent = null;
  let messageListComponent = null;
  let chatInputComponent = null;

  // Create main app container
  const appContainer = document.createElement('div');
  appContainer.className = `chatbot-app theme-${theme}`;
  
  // Add app styles
  const appStyles = document.createElement('style');
  appStyles.textContent = `
    .chatbot-app {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1rem;
    }
    
    .chatbot-app.theme-light {
      background-color: #ffffff;
    }
    
    .chatbot-app.theme-dark {
      background-color: #1a1a1a;
      color: #ffffff;
    }
    
    .chat-header {
      text-align: center;
      margin-bottom: 1rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #dee2e6;
    }
    
    .chat-messages {
      flex: 1;
      min-height: 0;
    }
    
    .chat-input-section {
      padding: 1rem 0;
      border-top: 1px solid #dee2e6;
      background-color: #ffffff;
    }
    
    .error-banner {
      background-color: #f8d7da;
      border: 1px solid #f5c6cb;
      color: #721c24;
      padding: 0.75rem 1rem;
      border-radius: 0.375rem;
      margin-bottom: 1rem;
    }
    
    .error-banner .btn-close {
      float: right;
      padding: 0.25rem;
    }
    
    @media (max-width: 768px) {
      .chatbot-app {
        padding: 0.5rem;
      }
      
      .chat-interface {
        height: 500px;
      }
    }
  `;
  
  document.head.appendChild(appStyles);

  // Create error banner (hidden by default)
  const errorBanner = document.createElement('div');
  errorBanner.className = 'error-banner';
  errorBanner.style.display = 'none';
  
  const errorMessage = document.createElement('span');
  const errorCloseBtn = document.createElement('button');
  errorCloseBtn.type = 'button';
  errorCloseBtn.className = 'btn-close';
  errorCloseBtn.addEventListener('click', hideError);
  
  errorBanner.appendChild(errorMessage);
  errorBanner.appendChild(errorCloseBtn);

  // Create main interface container with sidebar layout
  const interfaceContainer = document.createElement('div');
  interfaceContainer.className = 'chat-interface d-flex';
  interfaceContainer.style.cssText = `
    height: 600px;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    overflow: hidden;
  `;

  // Create header
  const header = document.createElement('div');
  header.className = 'chat-header mb-3';
  
  const headerTitle = document.createElement('h4');
  headerTitle.className = 'mb-0';
  headerTitle.innerHTML = '<i class="fas fa-robot me-2"></i>ResHub AI Assistant';
  
  const headerSubtitle = document.createElement('p');
  headerSubtitle.className = 'text-muted mb-0 small';
  headerSubtitle.textContent = 'Ask me anything about research papers in our database';
  
  header.appendChild(headerTitle);
  header.appendChild(headerSubtitle);

  // Create sidebar for sessions
  const sidebar = document.createElement('div');
  sidebar.className = 'chat-sidebar';
  sidebar.style.cssText = `
    width: 280px;
    background-color: #f8f9fa;
    border-right: 1px solid #dee2e6;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  `;

  // Create main chat area
  const chatMain = document.createElement('div');
  chatMain.className = 'chat-main';
  chatMain.style.cssText = `
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #ffffff;
  `;

  // Create messages section
  const messagesSection = document.createElement('div');
  messagesSection.className = 'chat-messages';
  messagesSection.style.cssText = `
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    border-bottom: 1px solid #dee2e6;
  `;

  // Create input section
  const inputSection = document.createElement('div');
  inputSection.className = 'chat-input-section';
  inputSection.style.cssText = `
    padding: 1rem;
    background-color: #ffffff;
  `;

  // Add elements to main container
  chatMain.appendChild(messagesSection);
  chatMain.appendChild(inputSection);

  // Add sidebar and main area to interface container
  interfaceContainer.appendChild(sidebar);
  interfaceContainer.appendChild(chatMain);

  // Add all elements to app container
  appContainer.appendChild(errorBanner);
  appContainer.appendChild(header);
  appContainer.appendChild(interfaceContainer);
  
  // Clear container and add app
  container.innerHTML = '';
  container.appendChild(appContainer);

  /**
   * Show error message
   */
  function showError(message) {
    errorMessage.textContent = message;
    errorBanner.style.display = 'block';
    
    // Auto-hide after 10 seconds
    setTimeout(hideError, 10000);
  }

  /**
   * Hide error message
   */
  function hideError() {
    errorBanner.style.display = 'none';
  }

  /**
   * Initialize child components
   */
  async function initializeComponents() {
    try {
      // Initialize session manager
      sessionManager = SessionManager;
      
      // Initialize session list in sidebar
      chatHistoryComponent = ChatHistory(sidebar, {
        showSessions: true,
        showMessages: false,
        layout: 'vertical'
      });
      
      // Always create message list for main area
      messageListComponent = MessageList(messagesSection);
      
      // Create chat input
      chatInputComponent = ChatInput(inputSection);
      
      // Load initial data
      await sessionManager.loadSessions();
      
      // Load current session messages if available
      const state = chatStore.getState();
      if (state.currentSession) {
        await sessionManager.loadChatHistory(state.currentSession.session_id);
      }
      
    } catch (error) {
      console.error('Error initializing components:', error);
      showError(`Failed to initialize chat: ${error.message}`);
    }
  }

  /**
   * Handle state changes from store
   */
  function handleStateChange(state, changedKeys) {
    if (changedKeys.includes('error') && state.error) {
      showError(state.error);
      // Clear error after showing
      setTimeout(() => chatStore.clearError(), 100);
    }
    
    if (changedKeys.includes('currentSession')) {
      // Update header subtitle with session info
      if (state.currentSession?.title) {
        headerSubtitle.textContent = `Current session: ${state.currentSession.title}`;
      } else {
        headerSubtitle.textContent = 'Ask me anything about research papers in our database';
      }
    }
  }

  /**
   * Initialize application
   */
  async function initialize() {
    // Subscribe to store changes
    unsubscribe = chatStore.subscribe(handleStateChange, ['error', 'currentSession']);
    
    // Initialize components
    await initializeComponents();
    
    console.log('Chatbot App initialized');
  }

  /**
   * Destroy application
   */
  function destroy() {
    if (unsubscribe) {
      unsubscribe();
      unsubscribe = null;
    }
    
    // Destroy child components
    if (chatHistoryComponent) {
      chatHistoryComponent.destroy();
      chatHistoryComponent = null;
    }
    
    if (messageListComponent) {
      messageListComponent.destroy();
      messageListComponent = null;
    }
    
    if (chatInputComponent) {
      chatInputComponent.destroy();
      chatInputComponent = null;
    }
    
    // Remove styles
    const styleElement = document.querySelector('style');
    if (styleElement && styleElement.textContent.includes('.chatbot-app')) {
      styleElement.remove();
    }
    
    // Clear container
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    
    console.log('Chatbot App destroyed');
  }

  /**
   * Refresh all components
   */
  function refresh() {
    if (chatHistoryComponent) {
      chatHistoryComponent.refresh();
    }
    
    if (messageListComponent) {
      messageListComponent.refresh();
    }
  }

  /**
   * Focus input
   */
  function focusInput() {
    if (chatInputComponent) {
      chatInputComponent.focus();
    }
  }

  /**
   * Get current state
   */
  function getState() {
    return chatStore.getState();
  }

  /**
   * Toggle history sidebar
   */
  function toggleHistory() {
    if (historySidebar) {
      const isVisible = historySidebar.style.display !== 'none';
      historySidebar.style.display = isVisible ? 'none' : 'block';
    }
  }

  // Initialize app
  initialize().catch(error => {
    console.error('Failed to initialize app:', error);
    showError(`Failed to start chat application: ${error.message}`);
  });

  // Return component API
  return {
    destroy,
    refresh,
    focusInput,
    getState,
    toggleHistory,
    showError,
    hideError,
    element: appContainer
  };
}

export default App;
