/**
 * SessionList Component for ResHub Chatbot
 * 
 * Displays the list of chat sessions and handles session switching.
 * Integrates with SessionManager for session operations.
 */

import { chatStore } from '../store/chatStore.js';
import { SessionManager } from '../services/SessionManager.js';

/**
 * Create SessionList component
 * @param {HTMLElement} container - Container element to render into
 * @returns {Object} Component instance with methods
 */
export function SessionList(container) {
  if (!container) {
    throw new Error('SessionList requires a container element');
  }

  let unsubscribe = null;
  let sessionManager = null;

  // Create the sessions container
  const sessionsContainer = document.createElement('div');
  sessionsContainer.className = 'sessions-container';
  sessionsContainer.style.cssText = `
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 1rem;
  `;
  
  // Create header
  const header = document.createElement('div');
  header.className = 'sessions-header d-flex justify-content-between align-items-center mb-3';
  
  const title = document.createElement('h6');
  title.className = 'mb-0';
  title.textContent = 'Chat Sessions';
  
  const newSessionBtn = document.createElement('button');
  newSessionBtn.type = 'button';
  newSessionBtn.className = 'btn btn-sm btn-outline-primary';
  newSessionBtn.innerHTML = '<i class="fas fa-plus"></i> New';
  
  header.appendChild(title);
  header.appendChild(newSessionBtn);
  
  // Create sessions list
  const sessionsList = document.createElement('div');
  sessionsList.className = 'sessions-list';
  sessionsList.style.cssText = `
    flex: 1;
    overflow-y: auto;
    padding: 0 8px;
  `;
  
  // Create empty state
  const emptyState = document.createElement('div');
  emptyState.className = 'empty-state text-center text-muted py-3';
  emptyState.innerHTML = `
    <i class="fas fa-comment-alt fa-2x mb-2"></i>
    <p class="small mb-0">No chat sessions yet</p>
  `;
  
  // Create loading state
  const loadingState = document.createElement('div');
  loadingState.className = 'loading-state text-center py-3';
  loadingState.style.display = 'none';
  loadingState.innerHTML = `
    <div class="spinner-border spinner-border-sm" role="status"></div>
    <p class="small mt-2 mb-0">Loading sessions...</p>
  `;
  
  // Add elements to container
  sessionsContainer.appendChild(header);
  sessionsContainer.appendChild(loadingState);
  sessionsContainer.appendChild(emptyState);
  sessionsContainer.appendChild(sessionsList);
  container.appendChild(sessionsContainer);

  /**
   * Format timestamp for display
   */
  function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  }

  /**
   * Create a session item element
   */
  function createSessionItem(session) {
    const item = document.createElement('div');
    item.className = 'session-item mb-2';
    item.dataset.sessionId = session.session_id;
    
    const state = chatStore.getState();
    const isActive = state.currentSession?.session_id === session.session_id;
    
    const card = document.createElement('div');
    card.className = `card session-card ${isActive ? 'border-primary' : ''}`;
    card.style.cssText = 'cursor: pointer; transition: all 0.2s;';
    
    const cardBody = document.createElement('div');
    cardBody.className = 'card-body py-2 px-3';
    
    // Session title
    const titleElement = document.createElement('div');
    titleElement.className = `fw-medium small ${isActive ? 'text-primary' : 'text-dark'}`;
    titleElement.textContent = session.title || 'Untitled Session';
    titleElement.style.cssText = `
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 200px;
    `;
    
    // Session timestamp
    const timestampElement = document.createElement('div');
    timestampElement.className = 'text-muted';
    timestampElement.style.cssText = 'font-size: 0.75rem;';
    timestampElement.textContent = formatTimestamp(session.last_active || session.created_at);
    
    // Active indicator
    if (isActive) {
      const activeIndicator = document.createElement('div');
      activeIndicator.className = 'position-absolute top-0 end-0 mt-1 me-1';
      activeIndicator.innerHTML = '<i class="fas fa-circle text-primary" style="font-size: 0.5rem;"></i>';
      card.style.position = 'relative';
      card.appendChild(activeIndicator);
    }
    
    cardBody.appendChild(titleElement);
    cardBody.appendChild(timestampElement);
    card.appendChild(cardBody);
    item.appendChild(card);
    
    // Add click handler
    card.addEventListener('click', () => switchToSession(session.session_id));
    
    // Add hover effects
    card.addEventListener('mouseenter', () => {
      if (!isActive) {
        card.classList.add('border-secondary');
        card.style.backgroundColor = '#f8f9fa';
      }
    });
    
    card.addEventListener('mouseleave', () => {
      if (!isActive) {
        card.classList.remove('border-secondary');
        card.style.backgroundColor = '';
      }
    });
    
    return item;
  }

  /**
   * Switch to a different session
   */
  async function switchToSession(sessionId) {
    if (!sessionManager) return;
    
    try {
      await sessionManager.switchToSession(sessionId);
      renderSessions(); // Re-render to update active state
    } catch (error) {
      console.error('Error switching to session:', error);
      chatStore.setError(`Failed to switch to session: ${error.message}`);
    }
  }

  /**
   * Create a new session
   */
  async function createNewSession() {
    if (!sessionManager) return;
    
    try {
      await sessionManager.createSession('', true); // Clear messages for explicit new session
      renderSessions(); // Re-render to show new session
    } catch (error) {
      console.error('Error creating new session:', error);
      chatStore.setError(`Failed to create new session: ${error.message}`);
    }
  }

  /**
   * Render the sessions list
   */
  function renderSessions() {
    console.log('[DEBUG] renderSessions called');
    const state = chatStore.getState();
    const sessions = state.sessions || [];
    console.log('[DEBUG] Sessions from store:', sessions);
    console.log('[DEBUG] Sessions count:', sessions.length);
    
    // Clear previous sessions
    sessionsList.innerHTML = '';
    
    // Show loading state if needed
    if (state.isLoadingSessions) {
      loadingState.style.display = 'block';
      emptyState.style.display = 'none';
      return;
    } else {
      loadingState.style.display = 'none';
    }
    
    // Show empty state or sessions
    if (sessions.length === 0) {
      emptyState.style.display = 'block';
    } else {
      emptyState.style.display = 'none';
      
      // Sort sessions by last_active (most recent first)
      const sortedSessions = [...sessions].sort((a, b) => {
        const timeA = new Date(a.last_active || a.created_at || 0);
        const timeB = new Date(b.last_active || b.created_at || 0);
        return timeB - timeA;
      });
      
      // Initially show only first 10 sessions
      const initialCount = 10;
      const sessionsToShow = sortedSessions.slice(0, initialCount);
      const hasMoreSessions = sortedSessions.length > initialCount;
      
      // Render each session
      sessionsToShow.forEach(session => {
        const sessionItem = createSessionItem(session);
        sessionsList.appendChild(sessionItem);
      });
      
      // Add "Show More" button if there are more sessions
      if (hasMoreSessions) {
        const showMoreBtn = document.createElement('button');
        showMoreBtn.className = 'btn btn-sm btn-outline-secondary mt-2 w-100';
        showMoreBtn.innerHTML = `<i class="fas fa-chevron-down"></i> Show ${sortedSessions.length - initialCount} more sessions`;
        showMoreBtn.onclick = () => {
          // Clear and show all sessions
          sessionsList.innerHTML = '';
          sortedSessions.forEach(session => {
            const sessionItem = createSessionItem(session);
            sessionsList.appendChild(sessionItem);
          });
        };
        sessionsList.appendChild(showMoreBtn);
      }
    }
  }

  /**
   * Handle state changes from store
   */
  function handleStateChange(state, changedKeys) {
    console.log('[DEBUG] handleStateChange called with keys:', changedKeys);
    console.log('[DEBUG] Current state sessions:', state.sessions?.length || 0);
    
    if (changedKeys.includes('sessions') || 
        changedKeys.includes('currentSession') || 
        changedKeys.includes('isLoadingSessions')) {
      console.log('[DEBUG] Triggering renderSessions from state change');
      renderSessions();
    } else {
      console.log('[DEBUG] No relevant state changes, not rendering');
    }
  }

  /**
   * Initialize component
   */
  function initialize() {
    // Create session manager
    sessionManager = SessionManager;
    console.log('[DEBUG] SessionList initialize - sessionManager:', sessionManager);
    console.log('[DEBUG] SessionList initialize - newSessionBtn:', newSessionBtn);
    
    // Initialize session manager with chatStore
    console.log('[DEBUG] Initializing sessionManager with chatStore:', chatStore);
    sessionManager.initialize(chatStore);
    console.log('[DEBUG] SessionManager initialized with store');
    
    // Add event listeners
    console.log('[DEBUG] Adding event listener to newSessionBtn');
    newSessionBtn.addEventListener('click', createNewSession);
    console.log('[DEBUG] Event listener added successfully');
    
    // Subscribe to store changes
    unsubscribe = chatStore.subscribe(handleStateChange, [
      'sessions', 
      'currentSession', 
      'isLoadingSessions'
    ]);
    
    // Initial load
    renderSessions();
    
    // Load sessions if not already loaded
    if (!chatStore.getState().sessions.length) {
      sessionManager.loadSessions();
    }
    
    console.log('SessionList component initialized');
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
    newSessionBtn.removeEventListener('click', createNewSession);
    
    // Clear container
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    
    console.log('SessionList component destroyed');
  }

  /**
   * Refresh sessions list
   */
  function refresh() {
    if (sessionManager) {
      sessionManager.loadSessions();
    }
  }

  // Initialize component
  initialize();

  // Return component API
  return {
    destroy,
    refresh,
    element: sessionsContainer
  };
}

export default SessionList;
