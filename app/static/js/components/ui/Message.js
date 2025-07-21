/**
 * Message Component for ResHub Chatbot
 * 
 * Renders a single chat message bubble (user or AI).
 * Handles Markdown-to-HTML conversion and includes a "Copy" button.
 */

import { formatCitation } from '../services/responseParser.js';

/**
 * Simple markdown to HTML converter
 * @param {string} text - Markdown text
 * @returns {string} HTML string
 */
function markdownToHtml(text) {
  if (!text) return '';
  
  return text
    // Bold **text**
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Italic *text*
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Code `text`
    .replace(/`(.*?)`/g, '<code>$1</code>')
    // Links [text](url)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
    // Line breaks
    .replace(/\n/g, '<br>');
}

/**
 * Create a copy button element
 * @param {string} textToCopy - Text to copy to clipboard
 * @returns {HTMLElement} Copy button element
 */
function createCopyButton(textToCopy) {
  const button = document.createElement('button');
  button.className = 'btn btn-sm btn-outline-secondary copy-btn';
  button.innerHTML = '<i class="fas fa-copy"></i> Copy';
  button.type = 'button';
  
  button.addEventListener('click', async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    try {
      await navigator.clipboard.writeText(textToCopy);
      
      // Update button to show success (CRITICAL FIX: Update innerHTML correctly)
      const originalHTML = button.innerHTML;
      button.innerHTML = '<i class="fas fa-check"></i> Copied!';
      button.classList.remove('btn-outline-secondary');
      button.classList.add('btn-success');
      
      // Reset after 2 seconds
      setTimeout(() => {
        button.innerHTML = originalHTML;
        button.classList.remove('btn-success');
        button.classList.add('btn-outline-secondary');
      }, 2000);
      
    } catch (error) {
      console.error('Failed to copy text:', error);
      
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = textToCopy;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      
      button.innerHTML = '<i class="fas fa-check"></i> Copied!';
    }
  });
  
  return button;
}

/**
 * Create citations section
 * @param {Array} citations - Array of citation objects
 * @returns {HTMLElement} Citations container
 */
function createCitationsSection(citations) {
  if (!citations) return null;
  
  // Handle both string and array formats for backward compatibility
  let citationArray = [];
  if (typeof citations === 'string') {
    // Handle string format (old messages)
    if (citations.trim() === '') return null;
    citationArray = [citations];
  } else if (Array.isArray(citations)) {
    // Handle array format (new messages)
    if (citations.length === 0) return null;
    citationArray = citations;
  } else {
    // Handle unexpected formats
    return null;
  }
  
  const container = document.createElement('div');
  container.className = 'citations-section mt-3';
  
  const header = document.createElement('h6');
  header.className = 'citations-header';
  header.textContent = 'Citations:';
  container.appendChild(header);
  
  const list = document.createElement('ol');
  list.className = 'citations-list';
  
  citationArray.forEach((citation, index) => {
    const item = document.createElement('li');
    item.className = 'citation-item';
    
    const formattedCitation = formatCitation(citation);
    item.innerHTML = markdownToHtml(formattedCitation);
    
    list.appendChild(item);
  });
  
  container.appendChild(list);
  return container;
}

/**
 * Create extras section
 * @param {string} extras - Extras content
 * @returns {HTMLElement} Extras container
 */
function createExtrasSection(extras) {
  if (!extras || !extras.trim()) return null;
  
  const container = document.createElement('div');
  container.className = 'extras-section mt-3';
  
  const header = document.createElement('h6');
  header.className = 'extras-header';
  header.textContent = 'Additional Information:';
  container.appendChild(header);
  
  const content = document.createElement('div');
  content.className = 'extras-content';
  content.innerHTML = markdownToHtml(extras);
  container.appendChild(content);
  
  return container;
}

/**
 * Create feedback buttons
 * @param {string} messageId - Message ID
 * @param {Function} onFeedback - Feedback callback
 * @returns {HTMLElement} Feedback container
 */
function createFeedbackSection(messageId, onFeedback) {
  const container = document.createElement('div');
  container.className = 'feedback-section mt-2';
  
  const label = document.createElement('small');
  label.className = 'text-muted me-2';
  label.textContent = 'Was this helpful?';
  container.appendChild(label);
  
  const thumbsUp = document.createElement('button');
  thumbsUp.className = 'btn btn-sm btn-outline-success me-1';
  thumbsUp.innerHTML = '<i class="fas fa-thumbs-up"></i>';
  thumbsUp.addEventListener('click', () => onFeedback(messageId, 1));
  
  const thumbsDown = document.createElement('button');
  thumbsDown.className = 'btn btn-sm btn-outline-danger';
  thumbsDown.innerHTML = '<i class="fas fa-thumbs-down"></i>';
  thumbsDown.addEventListener('click', () => onFeedback(messageId, -1));
  
  container.appendChild(thumbsUp);
  container.appendChild(thumbsDown);
  
  return container;
}

/**
 * Create Message component
 * @param {Object} message - Message object
 * @param {Function} onFeedback - Feedback callback function
 * @returns {HTMLElement} Message element
 */
export function Message(message, onFeedback = null) {
  const messageElement = document.createElement('div');
  messageElement.className = `message ${message.type === 'user' ? 'user-message' : 'ai-message'} mb-3`;
  messageElement.dataset.messageId = message.id || message.log_id || message.chat_id;
  
  // Create message card
  const card = document.createElement('div');
  card.className = 'card';
  messageElement.appendChild(card);
  
  const cardBody = document.createElement('div');
  cardBody.className = 'card-body';
  card.appendChild(cardBody);
  
  // Message header with sender info
  const header = document.createElement('div');
  header.className = 'd-flex justify-content-between align-items-center mb-2';
  
  const sender = document.createElement('strong');
  sender.className = 'message-sender';
  sender.textContent = message.type === 'user' ? 'You' : 'ResHub AI';
  header.appendChild(sender);
  
  if (message.timestamp) {
    const timestamp = document.createElement('small');
    timestamp.className = 'text-muted';
    timestamp.textContent = new Date(message.timestamp).toLocaleTimeString();
    header.appendChild(timestamp);
  }
  
  cardBody.appendChild(header);
  
  // Message content
  const content = document.createElement('div');
  content.className = 'message-content';
  
  if (message.type === 'user') {
    // User message - simple text
    content.innerHTML = markdownToHtml(message.prompt || message.content || '');
  } else {
    // AI message - may have structured content
    const answer = message.answer || message.response || message.content || '';
    content.innerHTML = markdownToHtml(answer);
    
    // Add citations if present
    if (message.citations && message.citations.length > 0) {
      const citationsSection = createCitationsSection(message.citations);
      if (citationsSection) {
        content.appendChild(citationsSection);
      }
    }
    
    // Add extras if present
    if (message.extras) {
      const extrasSection = createExtrasSection(message.extras);
      if (extrasSection) {
        content.appendChild(extrasSection);
      }
    }
  }
  
  cardBody.appendChild(content);
  
  // Message actions
  const actions = document.createElement('div');
  actions.className = 'message-actions mt-2 d-flex justify-content-between align-items-center';
  
  // Copy button
  const textToCopy = message.type === 'user' 
    ? (message.prompt || message.content || '')
    : (message.answer || message.response || message.content || '');
    
  const copyButton = createCopyButton(textToCopy);
  actions.appendChild(copyButton);
  
  // Feedback buttons for AI messages
  if (message.type === 'ai' && onFeedback) {
    const feedbackSection = createFeedbackSection(
      message.id || message.log_id || message.chat_id, 
      onFeedback
    );
    actions.appendChild(feedbackSection);
  }
  
  cardBody.appendChild(actions);
  
  return messageElement;
}

export default Message;
