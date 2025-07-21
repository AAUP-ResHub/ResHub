/**
 * MessageList Component for ResHub Chatbot
 * 
 * Renders the list of messages and subscribes to chatStore for reactive updates.
 * Handles auto-scrolling to the bottom when new messages arrive.
 */

import { Message } from './Message.js';
import { chatStore } from '../store/chatStore.js';
import * as apiService from '../services/apiService.js';

/**
 * Create MessageList component
 * @param {HTMLElement} container - Container element to render into
 * @returns {Object} Component instance with methods
 */
export function MessageList(container) {
  if (!container) {
    throw new Error('MessageList requires a container element');
  }

  let isScrolledToBottom = true;
  let unsubscribe = null;

  // Create the messages container
  const messagesContainer = document.createElement('div');
  messagesContainer.className = 'messages-container';
  messagesContainer.style.cssText = `
    height: 400px;
    overflow-y: auto;
    padding: 1rem;
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
    background-color: #f8f9fa;
  `;

  // Create empty state message
  const emptyState = document.createElement('div');
  emptyState.className = 'empty-state text-center text-muted py-5';
  emptyState.innerHTML = `
    <i class="fas fa-comments fa-3x mb-3"></i>
    <h5>Start a conversation</h5>
    <p>Ask me anything about research papers in our database.</p>
  `;

  // Create loading indicator
  const loadingIndicator = document.createElement('div');
  loadingIndicator.className = 'loading-indicator text-center py-3';
  loadingIndicator.style.display = 'none';
  loadingIndicator.innerHTML = `
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">Loading...</span>
    </div>
    <p class="mt-2 text-muted">AI is thinking...</p>
  `;

  // Add elements to container
  messagesContainer.appendChild(emptyState);
  messagesContainer.appendChild(loadingIndicator);
  container.appendChild(messagesContainer);

  /**
   * Check if user has scrolled away from bottom
   */
  function updateScrollPosition() {
    const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
    isScrolledToBottom = scrollTop + clientHeight >= scrollHeight - 10; // 10px tolerance
  }

  /**
   * Scroll to bottom of messages
   * @param {boolean} force - Force scroll even if user scrolled away
   */
  function scrollToBottom(force = false) {
    if (force || isScrolledToBottom) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  /**
   * Handle feedback submission
   * @param {string} messageId - Message ID
   * @param {number} rating - 1 for positive, -1 for negative
   */
  async function handleFeedback(messageId, rating) {
    try {
      await apiService.submitFeedback(messageId, rating);
      
      // Update message in store to reflect feedback
      chatStore.updateMessage(messageId, { feedback: rating > 0 ? 'positive' : 'negative' });
      
      // Show success toast
      showToast('Feedback submitted', 'Thank you for your feedback!', 'success');
    } catch (error) {
      console.error('Error submitting feedback:', error);
      showToast('Error', 'Failed to submit feedback. Please try again.', 'error');
    }
  }

  /**
   * Simple toast notification
   */
  function showToast(title, message, type = 'info') {
    // Simple implementation - you can enhance this
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999;';
    toast.innerHTML = `
      <strong>${title}</strong> ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 3000);
  }

  /**
   * Render messages from current state
   */
  function renderMessages() {
    const state = chatStore.getState();
    const messages = state.messages || [];
    
    // Clear previous messages (except empty state and loading indicator)
    const messageElements = messagesContainer.querySelectorAll('.message');
    messageElements.forEach(el => el.remove());
    
    // Show/hide empty state
    if (messages.length === 0) {
      emptyState.style.display = 'block';
    } else {
      emptyState.style.display = 'none';
      
      // Render each message
      messages.forEach(message => {
        const messageElement = Message(message, handleFeedback);
        messagesContainer.insertBefore(messageElement, loadingIndicator);
      });
      
      // Scroll to bottom for new messages
      setTimeout(scrollToBottom, 100);
    }
    
    // Show/hide loading indicator
    loadingIndicator.style.display = state.isLoading ? 'block' : 'none';
  }

  /**
   * Handle state changes
   */
  function handleStateChange(state, changedKeys) {
    if (changedKeys.includes('messages') || changedKeys.includes('isLoading')) {
      renderMessages();
    }
  }

  /**
   * Initialize component
   */
  function initialize() {
    // Subscribe to store changes
    unsubscribe = chatStore.subscribe(handleStateChange, ['messages', 'isLoading']);
    
    // Add scroll listener
    messagesContainer.addEventListener('scroll', updateScrollPosition);
    
    // Initial render
    renderMessages();
    
    console.log('MessageList component initialized');
  }

  /**
   * Destroy component
   */
  function destroy() {
    if (unsubscribe) {
      unsubscribe();
      unsubscribe = null;
    }
    
    messagesContainer.removeEventListener('scroll', updateScrollPosition);
    
    // Clear container
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    
    console.log('MessageList component destroyed');
  }

  /**
   * Refresh messages
   */
  function refresh() {
    renderMessages();
  }

  /**
   * Add a message (convenience method)
   */
  function addMessage(message) {
    chatStore.addMessage(message);
  }

  /**
   * Clear all messages (convenience method)
   */
  function clearMessages() {
    chatStore.clearMessages();
  }

  // Initialize component
  initialize();

  // Return component API
  return {
    destroy,
    refresh,
    addMessage,
    clearMessages,
    scrollToBottom: () => scrollToBottom(true),
    element: messagesContainer
  };
}

export default MessageList;
