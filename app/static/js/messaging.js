/**
 * ResHub Messaging System JavaScript
 * Handles real-time features like typing indicators and message management
 */

// Track whether a message was recently sent to avoid refreshing too soon after sending
let recentlySentMessage = false;
let lastMessageId = null;

// Function to refresh conversation messages via AJAX
function refreshConversation() {
    const currentUrl = window.location.href;
    if (!currentUrl.includes('/messaging/messages/')) {
        return; // Not in a conversation view
    }
    
    // If we recently sent a message, skip this refresh cycle
    // This prevents wiping out new messages before they're properly saved
    if (recentlySentMessage) {
        console.log('Skipping refresh cycle because a message was recently sent');
        recentlySentMessage = false;
        return;
    }
    
    // Get user_id from URL
    const urlParts = currentUrl.split('/');
    const userId = urlParts[urlParts.length - 1].split('?')[0];
    
    // Remember the scroll position
    const chatContainer = document.getElementById('chat-container');
    const isScrolledToBottom = chatContainer && 
        (Math.abs(chatContainer.scrollHeight - chatContainer.clientHeight - chatContainer.scrollTop) < 10);
    
    fetch(`/messaging/messages/${userId}/partial`)
        .then(response => response.text())
        .then(html => {
            // Create a temporary container to parse the HTML
            const tempContainer = document.createElement('div');
            tempContainer.innerHTML = html;
            
            const newMessagesList = tempContainer.querySelector('.messages-list');
            const currentMessagesList = document.querySelector('.messages-list');
            
            // Only update if we have both message lists and there are actual changes
            if (chatContainer && newMessagesList && currentMessagesList) {
                // Check if we have new content before replacing
                if (newMessagesList.innerHTML !== currentMessagesList.innerHTML) {
                    currentMessagesList.innerHTML = newMessagesList.innerHTML;
                    
                    // Convert all timestamps to local time
                    convertTimestampsToLocalTime();
                    
                    // Maintain scroll position
                    if (isScrolledToBottom) {
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }
                }
            } else if (chatContainer && newMessagesList && !currentMessagesList) {
                // First time loading messages
                chatContainer.innerHTML = html;
                convertTimestampsToLocalTime();
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        })
        .catch(error => {
            console.error('Error refreshing conversation:', error);
        });
}

// Function to initialize all messaging features
function initMessaging() {
    // Set up UI controls
    setupMessageActions();
    
    // Convert all timestamps to local time
    convertTimestampsToLocalTime();
    
    console.log('Messaging features initialized');
}

/**
 * Global state to track if conversations have been initialized
 */
let conversationsInitialized = false;

/**
 * Real-time inbox management - handles fetching, displaying, and updating conversations
 */
const InboxManager = {
    /**
     * Initialize the inbox with event listeners and data
     */
    init: function() {
        if (conversationsInitialized) return;
        console.log('Initializing InboxManager');
        
        // Set initial state
        this.conversations = new Map();
        this.container = document.getElementById('conversations-list');
        this.lastUpdateTime = new Date(0); // Start with epoch time
        
        // Start polling if we're on the inbox page or have inbox elements
        if (this.container || document.querySelector('[data-user-id]')) {
            this.startPolling();
            conversationsInitialized = true;
        }
    },
    
    /**
     * Start polling for conversation updates
     */
    startPolling: function() {
        // Immediate initial update
        this.fetchAndUpdateConversations();
        
        // Set up polling interval (10 seconds)
        this.pollingInterval = setInterval(() => {
            this.fetchAndUpdateConversations();
        }, 10000);
    },
    
    /**
     * Fetch conversations from server and update the UI
     */
    fetchAndUpdateConversations: function() {
        fetch('/messaging/conversations-json')
            .then(response => response.json())
            .then(data => {
                if (!Array.isArray(data)) return;
                
                // Process conversations
                this.processConversationData(data);
                
                // Update the UI based on our processed data
                this.updateUI();
            })
            .catch(error => console.error('Error fetching conversations:', error));
    },
    
    /**
     * Process conversation data from the server
     */
    processConversationData: function(data) {
        // Convert the array to a Map for easier manipulation
        const newConversations = new Map();
        
        data.forEach(conv => {
            // Store the conversation in our map
            newConversations.set(conv.user_id.toString(), {
                userId: conv.user_id,
                username: conv.username,
                profilePhoto: conv.profile_photo,
                message: {
                    content: conv.message.content,
                    isFromMe: conv.message.is_from_me,
                    timestamp: new Date(conv.message.timestamp),
                    id: conv.message.id
                },
                unreadCount: conv.unread_count
            });
            
            // Check if this is newer than our last update
            const msgTime = new Date(conv.message.timestamp);
            if (msgTime > this.lastUpdateTime) {
                this.lastUpdateTime = msgTime;
            }
        });
        
        this.conversations = newConversations;
    },
    
    /**
     * Update the UI with our current conversation data
     */
    updateUI: function() {
        // If we're on the inbox page, update the full list
        if (this.container) {
            this.updateInboxPage();
        } else {
            // Otherwise, just update any conversation previews that exist on the page
            this.updateConversationPreviews();
        }
        
        // Always update unread badges
        this.updateUnreadBadges();
    },
    
    /**
     * Update the full inbox page with all conversations
     */
    updateInboxPage: function() {
        // Check if container exists
        if (!this.container) return;
        
        // If empty, show empty state
        if (this.conversations.size === 0) {
            this.container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-chat-left-text" style="font-size: 3rem; color: #ccc;"></i>
                    <p class="mt-3">No messages yet. Start a conversation with someone!</p>
                    <a href="/messaging/new-message" class="btn btn-primary mt-2">Start a Conversation</a>
                </div>
            `;
            return;
        }
        
        // Get current items and build a map
        const existingItems = {};
        const currentItems = this.container.querySelectorAll('[data-user-id]');
        currentItems.forEach(item => {
            const userId = item.getAttribute('data-user-id');
            existingItems[userId] = item;
        });
        
        // Create sorted array from map (newest first)
        const sortedConvs = Array.from(this.conversations.values())
            .sort((a, b) => b.message.timestamp - a.message.timestamp);
            
        // Process each conversation
        sortedConvs.forEach(conv => {
            // Check if this conversation already exists in the DOM
            if (existingItems[conv.userId]) {
                // Update existing item
                this.updateConversationItem(existingItems[conv.userId], conv);
                delete existingItems[conv.userId]; // Remove from pending updates
            } else {
                // Create a new item and add it
                const newItem = this.createConversationItem(conv);
                // Add to the beginning of the list
                if (this.container.firstChild) {
                    this.container.insertBefore(newItem, this.container.firstChild);
                } else {
                    this.container.appendChild(newItem);
                }
            }
        });
        
        // Remove any items that no longer exist
        Object.values(existingItems).forEach(item => item.remove());
    },
    
    /**
     * Create a new conversation item for the inbox
     */
    createConversationItem: function(conv) {
        const isUnread = conv.unreadCount > 0;
        const localTime = conv.message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const localDate = conv.message.timestamp.toLocaleDateString([], {month: 'short', day: 'numeric', year: 'numeric'});
        
        // Create profile photo HTML
        let photoHtml;
        if (conv.profilePhoto) {
            photoHtml = `<img src="${conv.profilePhoto}" alt="${conv.username}" class="rounded-circle avatar-sm">`;
        } else {
            // Default avatar with initials
            const initial = conv.username.charAt(0).toUpperCase();
            photoHtml = `<img src="https://ui-avatars.com/api/?name=${initial}&size=48&background=4a6fa5&color=fff" alt="${conv.username}" class="rounded-circle avatar-sm">`;
        }
        
        // Create message prefix
        const messagePrefix = conv.message.isFromMe ? '<span class="text-muted me-1">You:</span>' : '';
        
        // Create the element
        const item = document.createElement('a');
        item.href = `/messaging/messages/${conv.userId}`;
        item.className = `list-group-item list-group-item-action conversation ${isUnread ? 'unread' : ''}`;
        item.setAttribute('data-user-id', conv.userId);
        
        item.innerHTML = `
            <div class="d-flex w-100">
                <div class="me-3">
                    ${photoHtml}
                </div>
                
                <div class="flex-grow-1">
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">${conv.username}</h5>
                        <small data-timestamp="${conv.message.timestamp.toISOString()}">${localDate}</small>
                    </div>
                    
                    <div class="d-flex align-items-center">
                        ${messagePrefix}
                        <p class="mb-1 message-preview">${conv.message.content}</p>
                        
                        ${isUnread ? `<span class="badge bg-primary rounded-pill ms-2">${conv.unreadCount}</span>` : ''}
                    </div>
                    
                    <small class="text-muted" data-timestamp="${conv.message.timestamp.toISOString()}">${localTime}</small>
                </div>
            </div>
        `;
        
        return item;
    },
    
    /**
     * Update an existing conversation item with new data
     */
    updateConversationItem: function(element, conv) {
        if (!element) return;
        
        // Update unread state
        const isUnread = conv.unreadCount > 0;
        element.classList.toggle('unread', isUnread);
        
        // Update message content
        const previewEl = element.querySelector('.message-preview');
        if (previewEl) {
            previewEl.textContent = conv.message.content;
        }
        
        // Update timestamps
        const timestamps = element.querySelectorAll('[data-timestamp]');
        timestamps.forEach(ts => {
            ts.setAttribute('data-timestamp', conv.message.timestamp.toISOString());
            
            // Format based on which timestamp element this is
            if (ts.tagName.toLowerCase() === 'small' && ts.classList.contains('text-muted')) {
                // Time only
                ts.textContent = conv.message.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            } else {
                // Date
                ts.textContent = conv.message.timestamp.toLocaleDateString([], {month: 'short', day: 'numeric', year: 'numeric'});
            }
        });
        
        // Update unread badge
        const badge = element.querySelector('.badge');
        if (isUnread) {
            if (badge) {
                badge.textContent = conv.unreadCount;
            } else {
                const badgeContainer = element.querySelector('.d-flex.align-items-center');
                if (badgeContainer) {
                    const newBadge = document.createElement('span');
                    newBadge.className = 'badge bg-primary rounded-pill ms-2';
                    newBadge.textContent = conv.unreadCount;
                    badgeContainer.appendChild(newBadge);
                }
            }
        } else if (badge) {
            badge.remove();
        }
        
        // Make sure prefix is correct
        const existingPrefix = element.querySelector('.text-muted.me-1');
        const needsPrefix = conv.message.isFromMe;
        
        if (needsPrefix && !existingPrefix) {
            const msgContainer = element.querySelector('.d-flex.align-items-center');
            if (msgContainer && previewEl) {
                const prefix = document.createElement('span');
                prefix.className = 'text-muted me-1';
                prefix.textContent = 'You:';
                msgContainer.insertBefore(prefix, previewEl);
            }
        } else if (!needsPrefix && existingPrefix) {
            existingPrefix.remove();
        }
    },
    
    /**
     * Update conversation previews on pages other than the inbox
     */
    updateConversationPreviews: function() {
        const previews = document.querySelectorAll('[data-user-id]');
        if (!previews.length) return;
        
        previews.forEach(preview => {
            const userId = preview.getAttribute('data-user-id');
            const conv = this.conversations.get(userId);
            if (conv) {
                this.updateConversationItem(preview, conv);
            }
        });
    },
    
    /**
     * Update unread badge counts in the navigation
     */
    updateUnreadBadges: function() {
        // Calculate total unread count
        let totalUnread = 0;
        this.conversations.forEach(conv => {
            totalUnread += conv.unreadCount;
        });
        
        // Update global badge
        const globalBadge = document.querySelector('#messages-badge');
        if (globalBadge) {
            if (totalUnread > 0) {
                globalBadge.textContent = totalUnread;
                globalBadge.style.display = 'inline-block';
            } else {
                globalBadge.style.display = 'none';
            }
        }
    },
    
    /**
     * Update the conversations with a new message (without waiting for poll)
     */
    updateWithNewMessage: function(userId, content, timestamp) {
        // Create a new conversation if it doesn't exist
        if (!this.conversations.has(userId.toString())) {
            // We need to fetch user info first
            fetch(`/messaging/user/${userId}/info`)
                .then(response => response.json())
                .then(userData => {
                    // Create new conversation entry
                    this.conversations.set(userId.toString(), {
                        userId: userId,
                        username: userData.username,
                        profilePhoto: userData.profile_photo,
                        message: {
                            content: content,
                            isFromMe: true,
                            timestamp: new Date(timestamp),
                            id: 'temp-' + Date.now()
                        },
                        unreadCount: 0
                    });
                    
                    // Update UI with new conversation
                    this.updateUI();
                });
        } else {
            // Update existing conversation
            const conv = this.conversations.get(userId.toString());
            conv.message = {
                content: content,
                isFromMe: true,
                timestamp: new Date(timestamp),
                id: conv.message.id
            };
            
            // Update UI with modified conversation
            this.updateUI();
        }
    }
};

/**
 * Convert all message timestamps from UTC to local time
 * This uses the data-timestamp attribute which contains ISO format timestamps
 */
function convertTimestampsToLocalTime() {
    // Find all elements with a data-timestamp attribute
    const timestampElements = document.querySelectorAll('[data-timestamp]');
    
    // Loop through all timestamp elements and convert to local time
    timestampElements.forEach(element => {
        const utcTimestamp = element.getAttribute('data-timestamp');
        if (utcTimestamp) {
            try {
                // Parse the UTC timestamp and convert to local time
                const date = new Date(utcTimestamp);
                if (!isNaN(date)) {
                    // Format the time in 12-hour format with AM/PM
                    const formattedTime = date.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    element.textContent = formattedTime;
                }
            } catch (error) {
                console.error('Error converting timestamp:', error);
            }
        }
    });
}

/**
 * Update the unread message count badge in the header navigation
 */
function updateUnreadCount() {
    // Send a request to update the unread badge count
    fetch('/messaging/unread-count')
        .then(response => response.json())
        .then(data => {
            // Update any unread badge in the header
            const unreadBadge = document.querySelector('#messages-badge');
            if (unreadBadge) {
                if (data.count > 0) {
                    unreadBadge.textContent = data.count;
                    unreadBadge.style.display = 'inline-block';
                } else {
                    unreadBadge.style.display = 'none';
                }
            }
        });
}

/**
 * Update inbox conversation preview after sending a new message
 * @deprecated Use InboxManager.updateWithNewMessage instead
 */
function updateInboxPreview(receiverId, messageContent, timestamp) {
    // For backward compatibility, use the new InboxManager
    InboxManager.updateWithNewMessage(receiverId, messageContent, timestamp);
}

/**
 * When the DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    // Convert all timestamps to local time
    convertTimestampsToLocalTime();
    
    // Initialize the InboxManager for real-time inbox updates
    InboxManager.init();
    
    // Setup message form if on messages page
    setupMessageForm();
    
    // Setup message refresh (disabled - function not implemented)
    // setupMessageRefresh();
    
    // Typing indicator functionality
    setupTypingIndicator();
    
    // Message actions (edit, delete)
    setupMessageActions();
    
    // Set up AJAX message submission (already called above)
    // setupMessageForm();
    
    // InboxManager already handles inbox refreshing and real-time updates
    // The initialization is done at the top of this DOMContentLoaded handler
});

/**
 * Sets up the typing indicator functionality with debounce
 */
function setupTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    const messageInput = document.getElementById('message-content');
    const receiverId = document.querySelector('input[name="receiver_id"]')?.value;
    
    if (!messageInput || !receiverId) return;
    
    let typingTimeout;
    let isTyping = false;
    
    // Function to send typing status to the server
    function updateTypingStatus(typing) {
        if (isTyping === typing) return;
        
        isTyping = typing;
        const formData = new FormData();
        formData.append('user_id', receiverId);
        formData.append('is_typing', typing);
        
        // Send typing status via fetch
        fetch('/messaging/typing-status', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
    }
    
    // Add input listener with debounce
    messageInput.addEventListener('input', function() {
        clearTimeout(typingTimeout);
        
        // Update status to typing
        updateTypingStatus(true);
        
        // Set timeout to stop typing indicator
        typingTimeout = setTimeout(() => {
            updateTypingStatus(false);
        }, 1500);
    });
    
    // Poll for other user's typing status
    if (typingIndicator && receiverId) {
        setInterval(() => {
            fetch(`/messaging/check-typing-status/${receiverId}`)
                .then(response => response.json())
                .then(data => {
                    typingIndicator.style.display = data.is_typing ? 'block' : 'none';
                })
                .catch(err => console.error('Error checking typing status:', err));
        }, 3000);
    }
}

/**
 * Set up message action handlers (edit, delete)
 */
function setupMessageActions() {
    // Delete message functionality
    setupDeleteMessages();
    
    // Edit message functionality
    setupEditMessages();
}

/**
 * Set up delete message functionality
 */
function setupDeleteMessages() {
    const deleteButtons = document.querySelectorAll('.delete-message-btn');
    const deleteForm = document.getElementById('delete-message-form');
    
    if (!deleteForm) return;
    
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const messageId = this.dataset.messageId;
            
            // If using a modal
            const deleteModal = document.getElementById('deleteMessageModal');
            if (deleteModal) {
                deleteForm.action = `/messaging/delete-message/${messageId}`;
                const bsModal = new bootstrap.Modal(deleteModal);
                bsModal.show();
            } else {
                // Direct deletion with confirmation
                if (confirm('Are you sure you want to delete this message?')) {
                    const formData = new FormData();
                    
                    // Send delete request via fetch
                    fetch(`/messaging/delete-message/${messageId}`, {
                        method: 'POST',
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            // Remove the message from the DOM
                            const messageContainer = document.getElementById(`message-${messageId}`);
                            if (messageContainer) {
                                messageContainer.remove();
                            }
                        }
                    });
                }
            }
        });
    });
}

/**
 * Set up edit message functionality
 */
function setupEditMessages() {
    // Use event delegation to handle edit buttons that might be dynamically added
    document.addEventListener('click', function(e) {
        // Find the edit button that was clicked (or its child icon)
        const editButton = e.target.closest('.edit-message-btn');
        if (!editButton) return;
        
        e.preventDefault();
        const messageId = editButton.dataset.messageId;
        const messageBubble = document.querySelector(`#message-${messageId} .message-bubble`);
        const messageContent = messageBubble.querySelector('.message-content');
        const originalContent = messageContent.textContent.trim();
        
        // Hide message actions while editing
        const messageActions = messageBubble.querySelector('.message-actions');
        if (messageActions) {
            messageActions.style.display = 'none';
        }
        
        // Replace content with edit form
        const editForm = document.createElement('form');
        editForm.classList.add('edit-message-form');
        editForm.innerHTML = `
            <textarea class="form-control mb-2">${originalContent}</textarea>
            <div class="d-flex justify-content-end">
                <button type="button" class="btn btn-sm btn-secondary me-2 cancel-edit-btn">Cancel</button>
                <button type="submit" class="btn btn-sm btn-primary save-edit-btn">Save</button>
            </div>
        `;
        
        // Save original content to restore on cancel
        messageContent.dataset.originalContent = originalContent;
        messageContent.innerHTML = '';
        messageContent.appendChild(editForm);
        
        // Focus on textarea
        const textarea = messageContent.querySelector('textarea');
        textarea.focus();
        
        // Handle cancel button
        const cancelBtn = messageContent.querySelector('.cancel-edit-btn');
        cancelBtn.addEventListener('click', function() {
            // Restore original content
            messageContent.innerHTML = messageContent.dataset.originalContent;
            
            // Show message actions again
            if (messageActions) {
                messageActions.style.display = '';
            }
        });
        
        // Handle form submission
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const newContent = textarea.value.trim();
            if (!newContent) return;
            
            // Send edit request via fetch
            const formData = new FormData();
            formData.append('content', newContent);
            
            fetch(`/messaging/edit-message/${messageId}`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update the message content and properly exit edit mode
                    messageContent.innerHTML = newContent;
                    
                    // Show message actions again
                    if (messageActions) {
                        messageActions.style.display = '';
                    }
                } else {
                    // Restore original content if there was an error
                    messageContent.innerHTML = messageContent.dataset.originalContent;
                    // Show message actions again
                    if (messageActions) {
                        messageActions.style.display = '';
                    }
                }
            })
            .catch(error => {
                console.error('Error updating message:', error);
                // Always restore to original state on error
                messageContent.innerHTML = messageContent.dataset.originalContent;
                // Show message actions again
                if (messageActions) {
                    messageActions.style.display = '';
                }
            });
        });
    });
}

/**
 * Set up AJAX message submission for instant display
 */
function setupMessageForm() {
    const messageForm = document.getElementById('send-message-form');
    const chatContainer = document.getElementById('chat-container');
    const messagesList = document.querySelector('.messages-list');
    const messageInput = document.getElementById('message-content');
    
    if (!messageForm || !chatContainer) return;
    
    // Create messages list if it doesn't exist (first message)
    if (!messagesList && chatContainer) {
        const newMessagesList = document.createElement('div');
        newMessagesList.className = 'messages-list';
        chatContainer.innerHTML = ''; // Clear 'No messages yet' text
        chatContainer.appendChild(newMessagesList);
    }
    
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const content = messageInput.value.trim();
        if (!content) return;
        
        const receiverId = messageForm.querySelector('input[name="receiver_ids[]"]').value;
        const formData = new FormData(messageForm);
        
        // Send message via AJAX
        // Set the flag to indicate a message was just sent
        // This will prevent refreshConversation from running immediately after sending
        recentlySentMessage = true;
        
        fetch('/messaging/send-message', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Store the latest message ID
                lastMessageId = data.message_id;
                // Clear the input field
                messageInput.value = '';
                
                // Use server's timestamp if available, otherwise use current time
                const serverTime = data.timestamp ? new Date(data.timestamp) : new Date();
                // Convert to local time using the same format as our converter function
                const timeString = serverTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                const messageId = data.message_id || `new-${Date.now()}`;
                
                // Create a new message element
                const messageContainer = document.createElement('div');
                messageContainer.className = 'message-container';
                messageContainer.id = `message-${messageId}`;
                
                // Create message bubble with sent styling
                const messageBubble = document.createElement('div');
                messageBubble.className = 'message-bubble message-sent';
                
                // Add message actions for sent messages
                const messageActions = document.createElement('div');
                messageActions.className = 'message-actions';
                messageActions.innerHTML = `
                    <button class="btn btn-sm text-white edit-message" data-message-id="${messageId}">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm text-white delete-message" data-message-id="${messageId}" data-bs-toggle="modal" data-bs-target="#deleteMessageModal">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
                messageBubble.appendChild(messageActions);
                
                // Create message content
                const messageContent = document.createElement('div');
                messageContent.className = 'message-content';
                messageContent.textContent = content;
                
                // Create message time with proper timestamp metadata
                const messageTime = document.createElement('div');
                messageTime.className = 'message-time';
                // Store the ISO timestamp as a data attribute for future conversions
                messageTime.setAttribute('data-timestamp', serverTime.toISOString());
                messageTime.textContent = timeString;
                
                // Assemble the message
                messageBubble.appendChild(messageContent);
                messageBubble.appendChild(messageTime);
                messageContainer.appendChild(messageBubble);
                
                // Add to the messages list (either existing or newly created)
                const currentMessagesList = document.querySelector('.messages-list') || 
                                          document.createElement('div');
                
                if (!currentMessagesList.parentElement) {
                    currentMessagesList.className = 'messages-list';
                    chatContainer.innerHTML = ''; // Clear any 'no messages' text
                    chatContainer.appendChild(currentMessagesList);
                }
                
                // Add the new message to the end of the list (at the bottom)
                currentMessagesList.appendChild(messageContainer);
                
                // Set flag to indicate we've just sent a message to prevent refresh flicker
                recentlySentMessage = true;
                setTimeout(() => { recentlySentMessage = false; }, 2000);
                
                // Use the InboxManager to update the UI instantly without waiting for polling
                // This ensures the conversation appears at the top of the inbox list immediately
                // and the message preview is updated with the latest message
                InboxManager.updateWithNewMessage(receiverId, content, serverTime.toISOString());
                
                // Also perform a full refresh in the background to ensure everything is up to date
                // This handles any edge cases like new conversations or multiple device updates
                setTimeout(() => {
                    InboxManager.fetchAndUpdateConversations();
                }, 1000);
                
                // Scroll to bottom of chat
                setTimeout(() => {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }, 100); // Short delay to ensure DOM update
            }
        })
        .catch(error => {
            console.error('Error sending message:', error);
        });
    });
    
    // Set up auto-refresh for conversation every 10 seconds
    setInterval(refreshConversation, 10000);
}
