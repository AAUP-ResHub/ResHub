// Notifications system for ResHub
class NotificationManager {
    constructor() {
        this.updateInterval = 30000; // 30 seconds
        this.csrfToken = this.getCsrfToken();
        this.init();
    }

    getCsrfToken() {
        // Get CSRF token from meta tag or cookie
        const token = document.querySelector('meta[name=csrf-token]');
        if (token) {
            return token.getAttribute('content');
        }
        // Fallback: try to get from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return value;
            }
        }
        return '';
    }

    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        if (this.csrfToken) {
            headers['X-CSRFToken'] = this.csrfToken;
        }
        return headers;
    }

    init() {
        this.updateNotificationBadge();
        this.loadDropdownNotifications();
        this.setupEventListeners();
        
        // Update notifications every 30 seconds
        setInterval(() => {
            this.updateNotificationBadge();
            this.loadDropdownNotifications();
        }, 30000);
    }

    setupEventListeners() {
        // Mark all as read in dropdown
        const markAllBtn = document.getElementById('markAllReadDropdown');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', () => {
                this.markAllAsRead();
            });
        }

        // Reload notifications when dropdown is opened
        const dropdown = document.getElementById('notificationDropdown');
        if (dropdown) {
            dropdown.addEventListener('show.bs.dropdown', () => {
                this.loadDropdownNotifications();
            });
        }
    }

    updateNotificationBadge() {
        fetch('/api/notifications?limit=1', {
            headers: this.getHeaders()
        })
            .then(response => response.json())
            .then(data => {
                const badge = document.getElementById('notification-badge');
                if (badge && data.unread_count !== undefined) {
                    const unreadCount = data.unread_count || 0;
                    if (unreadCount > 0) {
                        badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
                        badge.style.display = 'inline-block';
                    } else {
                        badge.style.display = 'none';
                    }
                }
            })
            .catch(error => {
                console.error('Error updating notification badge:', error);
            });
    }

    loadDropdownNotifications() {
        const container = document.getElementById('notificationDropdownList');
        if (!container) return;

        this.showDropdownLoading(container);
        
        fetch('/api/notifications?limit=5', {
            headers: this.getHeaders()
        })
            .then(response => response.json())
            .then(data => {
                if (data.notifications !== undefined) {
                    this.renderDropdownNotifications(data.notifications, container);
                } else {
                    this.showDropdownError(container);
                }
            })
            .catch(error => {
                console.error('Error loading dropdown notifications:', error);
                this.showDropdownError(container);
            });
    }

    renderDropdownNotifications(notifications, container) {
        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="p-3 text-center">
                    <i class="bi bi-bell text-muted" style="font-size: 2rem;"></i>
                    <p class="mt-2 mb-0 text-muted small">No new notifications</p>
                </div>
            `;
            return;
        }

        container.innerHTML = notifications.map(notification => `
            <div class="notification-item p-3 border-bottom ${ !notification.is_read ? 'bg-light' : '' }" 
                 style="cursor: pointer;" 
                 onclick="window.location.href='/notifications'">
                <div class="d-flex align-items-start">
                    <div class="flex-shrink-0 me-2">
                        <i class="bi ${ this.getNotificationIcon(notification.type) } text-primary"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="mb-1 fw-normal">${ notification.title || 'Notification' }</h6>
                        <p class="mb-1 text-muted small">${ this.truncateText(notification.message, 60) }</p>
                        <small class="text-muted">${ this.formatTime(notification.created_at) }</small>
                    </div>
                    ${ !notification.is_read ? '<div class="flex-shrink-0"><span class="badge bg-primary rounded-pill" style="width: 8px; height: 8px;"></span></div>' : '' }
                </div>
            </div>
        `).join('');
    }

    showDropdownLoading(container) {
        container.innerHTML = `
            <div class="p-3 text-center">
                <div class="spinner-border spinner-border-sm text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 mb-0 text-muted small">Loading notifications...</p>
            </div>
        `;
    }

    showDropdownError(container) {
        container.innerHTML = `
            <div class="p-3 text-center">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
                <p class="mt-2 mb-0 text-muted small">Failed to load notifications</p>
            </div>
        `;
    }

    getNotificationIcon(type) {
        switch(type) {
            case 'message': return 'bi-chat-left-text-fill';
            case 'paper': return 'bi-file-earmark-text-fill';
            case 'workspace': return 'bi-people-fill';
            case 'forum': return 'bi-chat-square-text-fill';
            default: return 'bi-bell-fill';
        }
    }

    truncateText(text, maxLength) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
        if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
        return date.toLocaleDateString();
    }

    markAllAsRead() {
        fetch('/api/notifications/mark-all-read', { 
            method: 'POST',
            headers: this.getHeaders()
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.updateNotificationBadge();
                    this.loadDropdownNotifications();
                    this.showToast('All notifications marked as read', 'success');
                } else {
                    this.showToast('Failed to mark notifications as read', 'error');
                }
            })
            .catch(error => {
                console.error('Error marking notifications as read:', error);
                this.showToast('Failed to mark notifications as read', 'error');
            });
    }

    showToast(message, type = 'success') {
        // Create a toast notification
        const toast = document.createElement('div');
        toast.className = 'toast show position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '1080';
        
        const bgClass = type === 'success' ? 'bg-success' : 'bg-danger';
        const icon = type === 'success' ? 'bi-check-circle' : 'bi-exclamation-triangle';
        
        toast.innerHTML = `
            <div class="toast-body ${bgClass} text-white">
                <i class="bi ${icon} me-2"></i>${message}
            </div>
        `;
        
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), type === 'success' ? 3000 : 5000);
    }

    showNotification(message, type = 'info') {
        // Create notification toast
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show notification-toast`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Add to notifications container
        const container = document.getElementById('notifications-container') || document.body;
        container.appendChild(notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize notification manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.notificationManager = new NotificationManager();
    console.log('Notification system loaded successfully');
});

// Export for other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationManager;
}
