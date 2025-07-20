// v3 unified handler - Consolidated initialization with timestamps
// ResHub Chatbot JavaScript
// Prevent multiple initializations with timestamp
const CHATBOT_SCRIPT_VERSION = 'v2025-06-26.1';
const INITIALIZATION_TIMESTAMP = Date.now();
window.chatbotInitialized = window.chatbotInitialized || false;

console.log(`Chatbot.js loaded successfully! ${CHATBOT_SCRIPT_VERSION}`);

// Master initialization function - will only run once
function initChatbotApp() {
  // Prevent multiple initializations using both flags and timestamps
  if (window.chatbotInitialized) {
    console.log('Chatbot already initialized, preventing duplicate initialization');
    return false;
  }
  
  console.log(`Chatbot initialization at timestamp: ${INITIALIZATION_TIMESTAMP}`);
  window.chatbotInitialized = true;
  
  // Setup localStorage for session persistence
  const savedSessionId = localStorage.getItem('currentSessionId');
  if (savedSessionId) {
    console.log('Restoring session from localStorage:', savedSessionId);
    window.currentSessionId = savedSessionId;
  }
  
  return true;
}


// Create chat-history container if it doesn't exist
function ensureChatHistoryContainer() {
  if (!document.getElementById('chat-history')) {
    console.log('Chat history container not found, creating one');
    
    // Try multiple possible parent containers
    const possibleParents = [
      document.querySelector('.sidebar-content'),
      document.querySelector('.chat-history-wrapper'),
      document.querySelector('.col-md-4'),
      document.querySelector('.card-body')
    ];
    
    // Find the first valid parent
    const parent = possibleParents.find(el => el !== null);
    
    if (parent) {
      const chatHistory = document.createElement('div');
      chatHistory.id = 'chat-history';
      chatHistory.className = 'list-group';
      parent.appendChild(chatHistory);
      console.log('Created missing chat-history container in', parent);
      return chatHistory;
    } else {
      console.error('Could not find a suitable parent for chat history container');
    }
  }
  
  return document.getElementById('chat-history');
}

// Try to ensure the container exists
document.addEventListener('DOMContentLoaded', ensureChatHistoryContainer);
ensureChatHistoryContainer(); // Also try immediately

// Track whether we've already added event listeners to prevent duplication
let chatHistoryEventsAdded = false;

// Add parent-level delegation for chat history clicks
function setupChatHistoryEvents() {
  // Don't add duplicate event handlers
  if (chatHistoryEventsAdded) {
    console.log('Chat history events already set up, skipping');
    return;
  }
  
  const chatHistoryContainer = document.getElementById('chat-history') || ensureChatHistoryContainer();
  if (chatHistoryContainer) {
    chatHistoryContainer.addEventListener('click', function(e) {
      const target = e.target.closest('.chat-history-item');
      if (target) {
        // Get both chat ID and session ID from the data attributes
        const chatId = target.dataset.chatId;
        const sessionId = target.dataset.sessionId;
        
        // Store the session ID if available
        if (sessionId) {
          window.currentSessionId = sessionId;
          localStorage.setItem('currentSessionId', sessionId);
        }
        
        // Now load the chat details
        if (typeof window.loadChatDetailsWithRetry === 'function') {
          window.loadChatDetailsWithRetry(chatId, 3).catch(err => {
            console.error('Final error in loadChatDetailsWithRetry:', err);
          });
        } else {
          // Fallback to original function
          loadChatDetails(chatId);
        }
      }
    });
    console.log('Added click delegation to chat history container with retry support');
    chatHistoryEventsAdded = true;
  } else {
    console.error('Could not find chat-history container for click delegation');
  }
}

// Add the event listener after DOM is loaded
document.addEventListener('DOMContentLoaded', setupChatHistoryEvents);

// Toast display counter to prevent duplicates
let toastDisplayCount = 0;

// Function to load chat details when clicking a chat history item
function loadChatDetails(chatId) {
  console.log('Loading chat details for ID:', chatId);
  // Prevent repeated clicks
  if (window.isLoadingChatDetails) {
    console.log('Already loading chat details, ignoring duplicate request');
    return;
  }
  
  window.isLoadingChatDetails = true;
  
  // Show loading in answer container
  const answerContainer = document.getElementById('answer-container');
  let answerContent = document.getElementById('answer-content');
  let citationsContent = document.getElementById('citations-content');
  let extrasContent = document.getElementById('extras-content');
  
  if (answerContainer) {
    // Remove d-none if present
    answerContainer.classList.remove('d-none');
    
    // Instead of replacing everything, ensure the structure exists
    // If these elements don't exist, create them fresh
    if (!answerContent) {
      // Clear container first
      answerContainer.innerHTML = '';
      
      // Create answer content div if missing
      answerContent = document.createElement('div');
      answerContent.id = 'answer-content';
      answerContent.className = 'answer-content';
      answerContainer.appendChild(answerContent);
      
      // Create citations content div if needed
      citationsContent = document.createElement('div');
      citationsContent.id = 'citations-content';
      citationsContent.className = 'citations-content mt-3 small';
      answerContainer.appendChild(citationsContent);
      
      // Create extras content div if needed
      extrasContent = document.createElement('div');
      extrasContent.id = 'extras-content';
      extrasContent.className = 'extras-content mt-3 small text-muted';
      answerContainer.appendChild(extrasContent);
    }
    
    // Now set loading state in answer content
    answerContent.innerHTML = `
      <div class="text-center">
        <div class="spinner-border text-primary" role="status"></div>
        <p class="mt-2">Loading previous chat...</p>
      </div>
    `;
  }
  
  // Don't use chatId as the session ID - it's not a UUID
  // We need to get the actual session ID from cached data if possible
  const cachedData = localStorage.getItem('lastChatHistory');
  let actualSessionId = null;
  
  if (cachedData) {
    try {
      const parsedCache = JSON.parse(cachedData);
      // Extract the session ID from the first chat entry
      if (Array.isArray(parsedCache) && parsedCache.length > 0) {
        actualSessionId = parsedCache[0].session_id;
        console.log('Extracted actual session ID from cache:', actualSessionId);
      }
    } catch (e) {
      console.error('Error parsing cached chat history:', e);
    }
  }
  
  // Use the extracted UUID session ID or fall back to whatever we have
  const currentSessionId = actualSessionId || window.currentSessionId || localStorage.getItem('currentSessionId');
  
  // Store the correct session ID format for future use
  if (actualSessionId) {
    localStorage.setItem('currentSessionId', actualSessionId);
    window.currentSessionId = actualSessionId;
  }
  
  // Fetch chat details from the API - fixed endpoint
  fetch(`/chatbot/api/chat/history?session_id=${currentSessionId}`)
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      console.log('Chat details response:', data);
      
      console.log('Response data structure:', Object.keys(data));
      
      // Check if the response contains expected structure
      if (!data) {
        throw new Error('Empty response from server');
      }
      
      // Find the specific chat entry - handle multiple possible response formats
      let chatData = {};
      
      // Case 1: {chats: Array} format (from our actual API)
      if (data.chats && Array.isArray(data.chats)) {
        // Try to find the specific chat with matching ID
        if (data.chats.length > 0) {
          // Find the chat by ID if possible
          const targetChat = data.chats.find(chat => chat.chat_id == chatId || chat.log_id == chatId);
          
          if (targetChat) {
            chatData = targetChat;
          } else {
            // Fall back to first chat if target not found
            console.log('Specific chat not found, using first available chat');
            chatData = data.chats[0];
          }
        } else {
          console.warn('Empty chat array returned from API, handling gracefully');
          chatData = {
            prompt: '',
            answer: 'No chat history available for this session. Try creating a new chat.',
            timestamp: new Date().toISOString()
          };
        }
      }
      // Case 2: Direct array format
      else if (Array.isArray(data)) {
        if (data.length > 0) {
          chatData = data[0];
        } else {
          console.warn('Empty direct array returned from API, handling gracefully');
          chatData = {
            prompt: '',
            answer: 'No chat history available for this session. Try creating a new chat.',
            timestamp: new Date().toISOString()
          };
        }
      } 
      // Case 3: {history: Array} format (our previous expectation)
      else if (data.history && Array.isArray(data.history)) {
        if (data.history.length > 0) {
          chatData = data.history[0];
        } else {
          console.warn('Empty history array returned from API, handling gracefully');
          chatData = {
            prompt: '',
            answer: 'No chat history available for this session. Try creating a new chat.',
            timestamp: new Date().toISOString()
          };
        }
      }
      // Case 4: Single chat object
      else if (data.prompt || data.answer || data.question || data.response) {
        chatData = data;
      }
      else {
        console.error('Unexpected response format:', data);
        throw new Error('Invalid response format from server');
      }
      
      console.log('Selected chat data:', chatData);
        
      // Update chat form with the original prompt
      const promptField = document.getElementById('prompt');
      if (promptField && chatData.prompt) {
        promptField.value = chatData.prompt || '';
      }
      
      // Update answer container with saved response
      if (answerContent) {
        // Check multiple possible field names
        const answer = chatData.answer || chatData.response || chatData.content || '';
        answerContent.innerHTML = answer;
      }
      
      if (citationsContent) {
        citationsContent.innerHTML = chatData.citations || '';
      }
      
      if (extrasContent) {
        extrasContent.innerHTML = chatData.extras || 
                               chatData.additional_info || 
                               'No additional information available.';
      }
      
      // Store chat ID for feedback and session tracking (multiple possible field names)
      window.currentChatId = chatId || chatData.chat_id || chatData.id;
      window.currentSessionId = chatData.session_id || chatId;
      
      // Enable feedback buttons if not already given
      const thumbsUp = document.getElementById('thumbs-up');
      const thumbsDown = document.getElementById('thumbs-down');
      
      if (thumbsUp && thumbsDown) {
        // Reset the buttons first
        thumbsUp.classList.remove('active');
        thumbsDown.classList.remove('active');
        thumbsUp.disabled = false;
        thumbsDown.disabled = false;
        
        if (chatData.feedback) {
          if (chatData.feedback === 'positive') {
            thumbsUp.classList.add('active');
            thumbsDown.disabled = true;
          } else if (chatData.feedback === 'negative') {
            thumbsDown.classList.add('active');
            thumbsUp.disabled = true;
          }
        }
      }
      
      // Show toast notification with counter to prevent duplicates
      const currentToastCount = ++toastDisplayCount;
      setTimeout(() => {
        // Only show toast if it's still the most recent one requested
        if (currentToastCount === toastDisplayCount) {
          const toastContainer = document.getElementById('toast-container');
          if (toastContainer) {
            // Create a simple toast message
            const toast = document.createElement('div');
            toast.className = 'toast show';
            toast.setAttribute('role', 'alert');
            toast.setAttribute('aria-live', 'assertive');
            toast.setAttribute('aria-atomic', 'true');
            
            toast.innerHTML = `
              <div class="toast-header">
                <strong class="me-auto">History</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
              </div>
              <div class="toast-body">
                Loaded previous chat response
              </div>
            `;
            
            // Add close button functionality
            const closeBtn = toast.querySelector('.btn-close');
            if (closeBtn) {
              closeBtn.addEventListener('click', () => {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 300);
              });
            }
            
            toastContainer.appendChild(toast);
            
            // Remove the toast after 3 seconds
            setTimeout(() => {
              toast.classList.remove('show');
              setTimeout(() => {
                toast.remove();
              }, 300);
            }, 3000);
          }
        }
      }, 100); // Small delay to prevent race conditions
    })
    .catch(error => {
      console.error('Error loading chat details:', error);
      if (answerContent) {
        answerContent.innerHTML = `<div class="alert alert-danger">Error loading chat: ${error.message}</div>`;
      }
    })
    .finally(() => {
      // Reset loading flag after slight delay to prevent rapid clicks
      setTimeout(() => {
        window.isLoadingChatDetails = false;
      }, 300);
    });
}

// Add retry mechanism for loadChatDetails
window.loadChatDetailsWithRetry = function(chatId, retryCount = 0) {
  const MAX_RETRIES = 2;
  
  return new Promise((resolve, reject) => {
    try {
      loadChatDetails(chatId);
      resolve();
    } catch (error) {
      console.error(`Error in loadChatDetails (attempt ${retryCount + 1}):`, error);
      
      if (retryCount < MAX_RETRIES) {
        console.log(`Retrying loadChatDetails in ${(retryCount + 1) * 500}ms...`);
        setTimeout(() => {
          window.loadChatDetailsWithRetry(chatId, retryCount + 1)
            .then(resolve)
            .catch(reject);
        }, (retryCount + 1) * 500);
      } else {
        console.error('Max retries reached for loadChatDetails');
        // Show error in UI
        const answerContent = document.getElementById('answer-content');
        if (answerContent) {
          answerContent.innerHTML = `<div class="alert alert-danger">Failed to load chat after multiple attempts.</div>`;
        }
        reject(error);
      }
    }
  }).finally(() => {
    // Always reset the loading flag
    window.isLoadingChatDetails = false;
  });
}

// Override the session list loading to handle missing elements
document.addEventListener('DOMContentLoaded', function() {
  // Safely get original function
  const originalLoadSessions = window.loadSessions;
  
  if (typeof originalLoadSessions === 'function') {
    // Override the loadSessions function
    window.loadSessions = function() {
      // First ensure containers exist
      ensureChatHistoryContainer();
      
      // Get or create session container
      let sessionList = document.getElementById('session-list');
      if (!sessionList) {
        console.warn('Session list container not found, creating a fallback');
        const sidebar = document.querySelector('.chat-sidebar');
        if (sidebar) {
          // Create a new container if missing
          sessionList = document.createElement('div');
          sessionList.id = 'session-list';
          sessionList.className = 'session-list';
          sidebar.appendChild(sessionList);
        } else {
          console.error('Chat sidebar not found, cannot create session list');
          return;
        }
      }
      
      const loadingElement = document.getElementById('loading-sessions');
      if (loadingElement) {
        loadingElement.style.display = 'block';
      }
      
      fetch('/chatbot/api/chat/sessions')
        .then(response => response.json())
        .then(data => {
          if (loadingElement) {
            loadingElement.style.display = 'none';
          }
          
          // Keep the first items (current session, divider, etc.)
          const elementsToKeep = Array.from(sessionList.children)
            .filter(el => el.id === 'current-session' || 
                        el.tagName === 'HR' ||
                        el.id === 'new-session' ||
                        el.id === 'loading-sessions');
          
          // Clear the list but keep important elements
          while (sessionList.firstChild) {
            sessionList.removeChild(sessionList.firstChild);
          }
          
          elementsToKeep.forEach(el => sessionList.appendChild(el));
          
          // Add sessions
          if (data.sessions && data.sessions.length > 0) {
            // Create divider if it doesn't exist
            let insertPosition = document.querySelector('#session-list hr');
            
            if (!insertPosition && sessionList) {
              // Add a divider if it doesn't exist
              const divider = document.createElement('hr');
              divider.className = 'dropdown-divider';
              sessionList.appendChild(divider);
              insertPosition = divider;
            }
            
            // Proceed with or without an insert position - if we have a valid session list
            if (sessionList) {
              data.sessions.forEach(session => {
                const sessionItem = document.createElement('li');
                const sessionLink = document.createElement('a');
                sessionLink.className = 'dropdown-item';
                sessionLink.href = '#';
                sessionLink.dataset.sessionId = session.session_id;
                sessionLink.textContent = session.title;
                
                // Add active class if this is the current session
                const currentSessionId = document.querySelector('#current-session')?.dataset.sessionId;
                if (session.session_id === currentSessionId) {
                  sessionLink.classList.add('active');
                }
                
                // Add click event to switch sessions
                sessionLink.addEventListener('click', function(e) {
                  e.preventDefault();
                  if (typeof window.switchSession === 'function') {
                    window.switchSession(session.session_id, session.title);
                  }
                });
                
                sessionItem.appendChild(sessionLink);
                if (insertPosition && insertPosition.parentNode) {
                  insertPosition.parentNode.insertBefore(sessionItem, insertPosition.nextSibling);
                } else {
                  // Fallback - just append to the list
                  sessionList.appendChild(sessionItem);
                }
              });
            } else {
              console.error('Session list container not available');
            }
          }
        })
        .catch(error => {
          if (loadingElement) {
            loadingElement.style.display = 'none';
          }
          
          // Log error but don't show toast
          console.error('Error loading sessions:', error);
        });
    };
    
    console.log('Sessions list loading function enhanced for reliability');
  }
});

// Ensure script runs after page is fully loaded
function attachFormListener() {
  console.log('Checking for chatbot form...');
  const chatForm = document.getElementById('chat-form');
  
  // Check if form exists
  if (!chatForm) {
    console.log('Chatbot form not found, will try again later.');
    return;
  }
  
  // Check if handler already attached to avoid duplicate handlers
  if (chatForm.hasAttribute('data-handler-attached')) {
    console.log('Handler already attached to form, skipping');
    return;
  }
  
  console.log('Found chatbot form, attaching handlers...');
  chatForm.setAttribute('data-handler-attached', 'true');
  
  // Add direct onsubmit handler
  chatForm.onsubmit = async function(e) {
    e.preventDefault();
    console.log('Form submitted - direct handler');
    
    const submitBtn = document.getElementById('submit-btn');
    const prompt = document.getElementById('prompt').value.trim();
    const loadingSpinner = document.getElementById('loading-spinner');
    const progressSteps = document.getElementById('progress-steps');
    const answerContainer = document.getElementById('answer-container');
    
    if (!prompt) {
      console.log('Empty prompt, not submitting');
      return false;
    }
    
    // Disable submit button and show loading indicators
    if (submitBtn) submitBtn.disabled = true;
    if (loadingSpinner) loadingSpinner.classList.remove('d-none');
    if (progressSteps) progressSteps.classList.remove('d-none');
    
    // Update progress step 1
    const step1 = document.getElementById('step1-progress');
    if (step1) step1.style.width = '100%';
    
    console.log('Sending request to API with prompt:', prompt);
    
    try {
      // Update progress step 2
      const step2 = document.getElementById('step2-progress');
      if (step2) setTimeout(() => { step2.style.width = '50%'; }, 300);
      
      // Get CSRF token from meta tag
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
      
      // Use the main production API endpoint with CSRF protection
      const headers = { 'Content-Type': 'application/json' };
      if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
      }
      
      const res = await fetch('/chatbot/api/chat', {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ 
          prompt: prompt,
          session_id: window.currentSessionId || null 
        })
      });
      
      // Finish progress step 2
      if (step2) step2.style.width = '100%';
      
      // Check if response is ok
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      // Update progress step 3
      const step3 = document.getElementById('step3-progress');
      if (step3) step3.style.width = '50%';
      
      const data = await res.json();
      console.log('API answer received:', data);

      // Finish progress step 3
      if (step3) step3.style.width = '100%';

      // Check if there was an error in the response
      if (data.error) {
        throw new Error(data.error);
      }

      // Update the answer container
      const answerContent = document.getElementById('answer-content');
      const citationsContent = document.getElementById('citations-content');
      
      if (answerContent && citationsContent && answerContainer) {
        answerContent.innerHTML = data.answer || 'No answer provided';
        citationsContent.innerHTML = data.citations || '';
        answerContainer.classList.remove('d-none');
      }
      
      // Append to chat history
      const chatHistory = document.getElementById('chat-history');
      if (chatHistory) {
        const noChatHistoryMsg = document.getElementById('no-chat-history-message');
        if (noChatHistoryMsg) {
          noChatHistoryMsg.classList.add('d-none');
        }
        
        // Store new session ID if returned from API
        if (data.session_id) {
          window.currentSessionId = data.session_id;
          // Always save the proper UUID session ID to localStorage
          localStorage.setItem('currentSessionId', data.session_id);
        }
        
        // Store chat ID for future reference
        window.currentChatId = data.chat_id;
        
        // Create element with appropriate data attributes
        chatHistory.insertAdjacentHTML('beforeend',
          `<button class="list-group-item list-group-item-action chat-history-item" 
             data-chat-id="${data.chat_id}" 
             data-session-id="${data.session_id || window.currentSessionId}">
             <div class="d-flex w-100 justify-content-between">
               <h6 class="mb-1 text-truncate">${prompt}</h6>
             </div>
             <small>Just now</small>
           </button>`);
        
        // Remove "no history" message if present
        const noHistoryMessage = chatHistory.querySelector('.no-history-message');
        if (noHistoryMessage) {
          noHistoryMessage.remove();
        }
      }
      
      // Reset form
      document.getElementById('prompt').value = '';
      
    } catch (err) {
      console.error('Error fetching response:', err);
      alert(`Error: ${err.message}. Please try again.`);
    } finally {
      // Hide loading indicators
      if (loadingSpinner) loadingSpinner.classList.add('d-none');
      if (progressSteps) progressSteps.classList.add('d-none');
      
      // Reset progress bars for next time
      const progressBars = document.querySelectorAll('.progress-bar');
      progressBars.forEach(bar => { bar.style.width = '0%'; });
      
      // Re-enable submit button
      if (submitBtn) submitBtn.disabled = false;
    }
    
    return false;
  };
  
  // Also use addEventListener as a backup approach
  chatForm.addEventListener('submit', function(e) {
    console.log('Form submit event fired via addEventListener');
    // Let the onsubmit handler above handle the actual submission
    // This is just for logging purposes
  });
  
  // Sessions list loading function enhanced for reliability
  const sessionList = document.getElementById('session-list');
  const loadingElement = document.getElementById('loading-sessions');
  
  // Fetch sessions
  fetch('/chatbot/api/chat/sessions')
    .then(data => {
      if (loadingElement) {
        loadingElement.style.display = 'none';
      }
      
      // Keep the first items (current session, divider, etc.)
      const elementsToKeep = Array.from(sessionList.children)
        .filter(el => el.id === 'current-session' || 
                    el.tagName === 'HR' ||
                    el.id === 'new-session' ||
                    el.id === 'loading-sessions');
      
      // Clear the list but keep important elements
      while (sessionList.firstChild) {
        sessionList.removeChild(sessionList.firstChild);
      }
      
      elementsToKeep.forEach(el => sessionList.appendChild(el));
      
      // Add sessions
      if (data.sessions && data.sessions.length > 0) {
        // Find insert position - after the divider
        const insertPosition = document.querySelector('#session-list hr');
        
        // Only proceed if we found the insert position
        if (insertPosition && insertPosition.parentNode) {
          data.sessions.forEach(session => {
            const sessionItem = document.createElement('li');
            const sessionLink = document.createElement('a');
            sessionLink.className = 'dropdown-item';
            sessionLink.href = '#';
            sessionLink.dataset.sessionId = session.session_id;
            sessionLink.textContent = session.title;
            
            // Add active class if this is the current session
            const currentSessionId = document.querySelector('#current-session')?.dataset.sessionId;
            if (session.session_id === currentSessionId) {
              sessionLink.classList.add('active');
            }
            
            // Add click event to switch sessions
            sessionLink.addEventListener('click', function(e) {
              e.preventDefault();
              if (typeof window.switchSession === 'function') {
                window.switchSession(session.session_id, session.title);
              }
            });
            
            sessionItem.appendChild(sessionLink);
            insertPosition.parentNode.insertBefore(sessionItem, insertPosition.nextSibling);
          });
        } else {
          console.error('Insert position for session items not found');
        }
      }
    })
    .catch(error => {
      if (loadingElement) {
        loadingElement.style.display = 'none';
      }
      
      // Log error but don't show toast
      console.error('Error loading sessions:', error);
    });
  
  console.log('Sessions list loading function enhanced for reliability');
}

// Call the function when script loads
attachFormListener();

// Also attach on DOM ready
document.addEventListener('DOMContentLoaded', attachFormListener);

// Expose necessary global functions

// Update chat history function
window.updateChatHistory = function() {
  console.log('Updating chat history...');
  
  // Get the session ID - check for valid UUID format first
  let sessionId = window.currentSessionId;
  
  // Quick check if it looks like a UUID (contains hyphens and is long enough)
  const isLikelyUUID = sessionId && typeof sessionId === 'string' && 
    sessionId.includes('-') && sessionId.length > 30;
  
  if (!isLikelyUUID) {
    // Try to get a valid session ID from cache
    try {
      const cachedData = localStorage.getItem('lastChatHistory');
      if (cachedData) {
        const parsedCache = JSON.parse(cachedData);
        if (Array.isArray(parsedCache) && parsedCache.length > 0) {
          // Use the session ID from the first chat entry
          sessionId = parsedCache[0].session_id;
          console.log('Using session ID from cache instead:', sessionId);
        }
      }
    } catch (e) {
      console.error('Error extracting session ID from cache:', e);
    }
  }
  
  if (!sessionId) {
    console.log('No valid session ID available, skipping history update');
    return;
  }
  
  // Save session ID to localStorage for persistence
  localStorage.setItem('currentSessionId', sessionId);
  window.currentSessionId = sessionId;
  console.log('Saved session ID to localStorage:', sessionId);
  
  const chatHistory = document.getElementById('chat-history');
  
  if (!chatHistory) {
    console.error('Chat history container not found');
    // Try to create the container
    const createdContainer = ensureChatHistoryContainer();
    if (!createdContainer) {
      console.error('Failed to create chat history container');
      return;
    }
    // Use the newly created container
    return window.updateChatHistory();
  }
  
  // Clear current history first (to avoid duplicates)
  while (chatHistory.firstChild) {
    chatHistory.removeChild(chatHistory.firstChild);
  }
  
  // Add loading indicator
  const loadingItem = document.createElement('div');
  loadingItem.className = 'alert alert-info';
  loadingItem.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"></div> Loading chat history...';
  chatHistory.appendChild(loadingItem);
  
  // Fetch the chat history
  fetch('/chatbot/api/chat/history?session_id=' + (window.currentSessionId || ''))
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      console.log('Chat history API response:', data);
      
      // Clear the loading indicator
      while (chatHistory.firstChild) {
        chatHistory.removeChild(chatHistory.firstChild);
      }
      
      let chatItems = [];
      
      // Handle different response formats
      if (data.chats && Array.isArray(data.chats)) {
        // Format: {chats: Array}
        chatItems = data.chats;
      } else if (Array.isArray(data)) {
        // Direct array format
        chatItems = data;
      } else if (data.history && Array.isArray(data.history)) {
        // Format: {history: Array}
        chatItems = data.history;
      }
      
      // Check if we got empty results but have cache available
      if (chatItems.length === 0) {
        console.log('API returned empty chat history, trying localStorage fallback');
        try {
          const cachedHistory = localStorage.getItem('lastChatHistory');
          if (cachedHistory) {
            const parsedCache = JSON.parse(cachedHistory);
            if (Array.isArray(parsedCache) && parsedCache.length > 0) {
              console.log('Using cached chat history from localStorage:', parsedCache.length, 'items');
              chatItems = parsedCache;
            }
          }
        } catch (e) {
          console.error('Error using cached history:', e);
        }
      }
      
      // Store the latest chat items in localStorage for fallback
      if (chatItems.length > 0) {
        // Save to localStorage for future fallback
        try {
          localStorage.setItem('lastChatHistory', JSON.stringify(chatItems));
          console.log('Saved chat history to localStorage');
        } catch (e) {
          console.warn('Failed to save chat history to localStorage:', e);
        }
        
        // Add new chat history items
        chatItems.forEach(item => {
          // Extract chat ID from various possible formats
          const chatId = item.chat_id || item.id || item.session_id;
          if (!chatId) {
            console.warn('Chat item missing ID:', item);
            return;
          }
          
          // Get text content for display
          const promptText = item.prompt || item.question || 'No prompt';
          const answerText = item.answer || item.response || 'No answer';
          const timestamp = item.timestamp || item.created_at || new Date().toISOString();
          
          const historyItem = document.createElement('button');
          historyItem.className = 'list-group-item list-group-item-action chat-history-item';
          historyItem.setAttribute('data-chat-id', chatId);
          historyItem.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
              <h6 class="mb-1">${promptText.substring(0, 30) + (promptText.length > 30 ? '...' : '')}</h6>
              <small>${new Date(timestamp).toLocaleTimeString()}</small>
            </div>
            <small class="text-muted">${answerText.replace ? answerText.replace(/<[^>]*>/g, '').substring(0, 50) + '...' : answerText}</small>
          `;
          
          chatHistory.appendChild(historyItem);
        });
      } else {
        // Try to recover from localStorage if API returned empty results
        try {
          const savedHistory = localStorage.getItem('lastChatHistory');
          if (savedHistory) {
            console.log('API returned no results, attempting to restore from localStorage');
            const savedItems = JSON.parse(savedHistory);
            
            if (savedItems && savedItems.length > 0) {
              console.log('Using cached chat history from localStorage');
              
              // Add notice about using cached data
              const cachedNotice = document.createElement('div');
              cachedNotice.className = 'alert alert-warning';
              cachedNotice.innerHTML = 'Showing cached chat history. <button class="btn btn-sm btn-outline-dark refresh-btn">Refresh</button>';
              chatHistory.appendChild(cachedNotice);
              
              // Add click handler to the refresh button
              const refreshBtn = cachedNotice.querySelector('.refresh-btn');
              if (refreshBtn) {
                refreshBtn.addEventListener('click', window.updateChatHistory);
              }
              
              // Display the cached items
              savedItems.forEach(item => {
                // Same rendering code as above
                const chatId = item.chat_id || item.id || item.session_id;
                if (!chatId) return;
                
                const promptText = item.prompt || item.question || 'No prompt';
                const answerText = item.answer || item.response || 'No answer';
                const timestamp = item.timestamp || item.created_at || new Date().toISOString();
                
                const historyItem = document.createElement('button');
                historyItem.className = 'list-group-item list-group-item-action chat-history-item cached-item';
                historyItem.setAttribute('data-chat-id', chatId);
                historyItem.innerHTML = `
                  <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${promptText.substring(0, 30) + (promptText.length > 30 ? '...' : '')}</h6>
                    <small>${new Date(timestamp).toLocaleTimeString()}</small>
                  </div>
                  <small class="text-muted">${answerText.replace ? answerText.replace(/<[^>]*>/g, '').substring(0, 50) + '...' : answerText}</small>
                `;
                
                chatHistory.appendChild(historyItem);
              });
              return;
            }
          }
        } catch (e) {
          console.warn('Failed to restore chat history from localStorage:', e);
        }
        
        // If we get here, there's truly no history or we couldn't restore it
        const noHistoryMsg = document.createElement('div');
        noHistoryMsg.className = 'alert alert-info no-history-message';
        noHistoryMsg.textContent = 'No chat history yet.';
        chatHistory.appendChild(noHistoryMsg);
      }
    })
    .catch(error => {
      console.error('Error fetching chat history:', error);
      
      // Clear and show error
      while (chatHistory.firstChild) {
        chatHistory.removeChild(chatHistory.firstChild);
      }
      
      const errorMsg = document.createElement('div');
      errorMsg.className = 'alert alert-danger';
      errorMsg.textContent = 'Error loading chat history: ' + error.message;
      chatHistory.appendChild(errorMsg);
    });
};

// Switch session function with robust error handling
window.switchSession = function(sessionId) {
  if (!sessionId) {
    console.error('Invalid session ID provided to switchSession');
    return;
  }
  
  console.log('Switching to session:', sessionId);
  
  // Store the previous session ID in case we need to revert
  const previousSessionId = window.currentSessionId;
  
  try {
    // Update current session and store in localStorage
    window.currentSessionId = sessionId;
    localStorage.setItem('currentSessionId', sessionId);
    
    // Update session display
    const currentSessionDisplay = document.getElementById('current-session-display');
    if (currentSessionDisplay) {
      currentSessionDisplay.textContent = 'Loading...';
      
      // Fetch session details with error handling
      fetch('/chatbot/api/chat/sessions')
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          if (!data || !data.sessions) {
            throw new Error('Invalid session data structure');
          }
          
          const session = data.sessions.find(s => s.session_id === sessionId);
          if (session) {
            // Update display and persist session info
            currentSessionDisplay.textContent = session.title || 'Untitled Session';
            localStorage.setItem('currentSessionTitle', session.title || 'Untitled Session');
          } else {
            // Session not found in response
            console.warn(`Session ${sessionId} not found in server response`);
            currentSessionDisplay.textContent = 'Untitled Session';
          }
        })
        .catch(error => {
          console.error('Error fetching session details:', error);
          // Try to get title from localStorage as fallback
          const savedTitle = localStorage.getItem('currentSessionTitle');
          if (savedTitle && currentSessionDisplay) {
            currentSessionDisplay.textContent = savedTitle;
          } else if (currentSessionDisplay) {
            currentSessionDisplay.textContent = 'Session ' + sessionId.substring(0, 8);
          }
        });
    }
    
    // Update chat history
    window.updateChatHistory();
    
  } catch (error) {
    // Handle any unexpected errors and revert if needed
    console.error('Error during session switch:', error);
    
    // Revert to previous session if possible
    if (previousSessionId) {
      console.log('Reverting to previous session:', previousSessionId);
      window.currentSessionId = previousSessionId;
      localStorage.setItem('currentSessionId', previousSessionId);
    }
    
    // Show error toast
    window.showToast('Error', 'Failed to switch session. Please try again.', 'danger');
  }
};

// Show toast function
window.showToast = function(title, message, type = 'info') {
  console.log(`Toast: ${title} - ${message} (${type})`);
  const toastContainer = document.getElementById('toast-container');
  if (!toastContainer) return;
  
  const toast = document.createElement('div');
  toast.className = `toast show bg-${type} text-white`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  
  toast.innerHTML = `
    <div class="toast-header bg-${type} text-white">
      <strong class="me-auto">${title}</strong>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
    <div class="toast-body">
      ${message}
    </div>
  `;
  
  toastContainer.appendChild(toast);
  
  // Remove after 5 seconds
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, 5000);
};

// Load sessions function
window.loadSessions = function() {
  console.log('Loading sessions...');
  let sessionsList = document.getElementById('sessions-list');
  
  // Enhanced container detection and creation
  if (!sessionsList) {
    console.warn('Sessions list container not found, looking for alternatives...');
    
    // Try multiple fallback containers
    const possibleContainers = [
      document.querySelector('.dropdown-menu'),
      document.querySelector('.session-dropdown'),
      document.querySelector('.navbar-nav .dropdown-menu')
    ];
    
    // Find the first valid container
    const fallbackContainer = possibleContainers.find(container => container !== null);
    
    if (fallbackContainer) {
      console.log('Found alternative dropdown menu, using that instead');
      renderSessions(fallbackContainer);
      return;
    } else {
      // Last resort - create the container
      console.warn('No suitable container found. Creating sessions-list container');
      
      // Find a parent for our new container
      const possibleParents = [
        document.querySelector('.navbar-nav'),
        document.querySelector('.session-menu'),
        document.querySelector('.dropdown'),
        document.body
      ];
      
      const parent = possibleParents.find(p => p !== null);
      
      if (parent) {
        sessionsList = document.createElement('div');
        sessionsList.id = 'sessions-list';
        sessionsList.className = 'dropdown-menu';
        parent.appendChild(sessionsList);
        console.log('Created sessions-list container in', parent);
      } else {
        console.error('Could not find a parent for sessions container');
        return;
      }
    }
  }
  
  renderSessions(sessionsList);
  
  // Helper function to render sessions in a container
  function renderSessions(container) {
    // Clear the existing content safely
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
    
    // Add loading indicator
    const loadingItem = document.createElement('div');
    loadingItem.className = 'dropdown-item text-center';
    loadingItem.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"></div>';
    container.appendChild(loadingItem);
    
    // Fetch the sessions with CSRF token
    // Get CSRF token from meta tag
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // Prepare headers with CSRF token for GET request
    const headers = {};
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
    
    fetch('/chatbot/api/chat/sessions', {
      method: 'GET',
      headers: headers
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        console.log('Sessions API response:', data);
        
        // Safely clear the loading indicator
        while (container.firstChild) {
          container.removeChild(container.firstChild);
        }
        
        if (data.sessions && data.sessions.length > 0) {
          // Add new sessions
          data.sessions.forEach(session => {
            const sessionItem = document.createElement('a');
            sessionItem.className = 'dropdown-item';
            sessionItem.href = '#';
            sessionItem.setAttribute('data-session-id', session.session_id);
            sessionItem.innerHTML = `
              ${session.title || 'Untitled Session'} 
              <small class="text-muted">${new Date(session.created_at || Date.now()).toLocaleDateString()}</small>
            `;
            
            // Use a safer click handler with capture and cleanup
            sessionItem.onclick = function(e) {
              e.preventDefault();
              e.stopPropagation();
              
              // Store in localStorage for persistence
              localStorage.setItem('currentSessionId', session.session_id);
              window.currentSessionId = session.session_id;
              
              // Call switchSession function (for backward compatibility)
              if (typeof window.switchSession === 'function') {
                window.switchSession(session.session_id);
              } else {
                // Fallback if switchSession doesn't exist
                window.updateChatHistory();
              }
              
              // Update UI
              const currentSessionDisplay = document.getElementById('current-session-display');
              if (currentSessionDisplay) {
                currentSessionDisplay.textContent = session.title || 'Untitled Session';
              }
              
              // Close dropdown if we're in one
              const dropdown = sessionItem.closest('.dropdown-menu');
              if (dropdown) {
                dropdown.classList.remove('show');
              }
            };
            
            container.appendChild(sessionItem);
          });
        } else {
          // No sessions
          const noSessionsMsg = document.createElement('div');
          noSessionsMsg.className = 'dropdown-item';
          noSessionsMsg.textContent = 'No sessions yet.';
          container.appendChild(noSessionsMsg);
        }
      })
      .catch(error => {
        console.error('Error fetching sessions:', error);
        
        // Safely clear and show error
        while (container.firstChild) {
          container.removeChild(container.firstChild);
        }
        
        const errorMsg = document.createElement('div');
        errorMsg.className = 'dropdown-item text-danger';
        errorMsg.textContent = 'Error loading sessions';
        container.appendChild(errorMsg);
      });
  }
};

// Run the initialization once before DOMContentLoaded in case script loads after DOM is ready
if (document.readyState === 'complete' || document.readyState === 'interactive') {
  console.log('Document already loaded, initializing immediately');
  runFullInitialization();
}

// Also set up for DOMContentLoaded for normal flow
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOMContentLoaded event fired');
  runFullInitialization();
});

// Full initialization function that only executes once
function runFullInitialization() {
  // Use our master initialization function that prevents duplicates
  if (!initChatbotApp()) {
    console.log('Chatbot already initialized via timestamp check, skipping');
    return;
  }
  
  console.log('Running full chatbot initialization');
  
  // Make loadChatDetails available globally
  window.loadChatDetails = loadChatDetails;
  
  // Ensure the chat history container exists
  const chatHistoryContainer = ensureChatHistoryContainer();
  
  // Set up chat history click handlers
  setupChatHistoryEvents();
  
  // Restore session from localStorage if available
  const savedSessionId = localStorage.getItem('currentSessionId');
  console.log('Restored session ID from localStorage:', savedSessionId);
  
  if (savedSessionId) {
    // Set current session ID
    window.currentSessionId = savedSessionId;
    
    // Update session display
    const currentSessionDisplay = document.getElementById('current-session-display');
    if (currentSessionDisplay) {
      currentSessionDisplay.textContent = 'Loading saved session...';
    }
    
    // Load chat history for the restored session
    console.log('Loading chat history for restored session:', savedSessionId);
    setTimeout(() => { 
      if (typeof window.updateChatHistory === 'function') {
        window.updateChatHistory();
      }
    }, 100);
    
    // Also load session details to update the UI
    fetch('/chatbot/api/chat/sessions')
      .then(response => response.json())
      .then(data => {
        if (data.sessions) {
          const session = data.sessions.find(s => s.session_id === savedSessionId);
          if (session && currentSessionDisplay) {
            currentSessionDisplay.textContent = session.title || 'Untitled Session';
          }
        }
      })
      .catch(err => console.error('Error loading session details:', err));
  }
  
  // Load available sessions list
  if (typeof window.loadSessions === 'function') {
    setTimeout(() => window.loadSessions(), 200);
  }
}
