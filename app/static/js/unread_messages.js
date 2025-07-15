/**
 * Script to update unread messages count in the navbar
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Loading unread message count script');
    // Only run if user is logged in (check for the unread messages count element)
    const unreadMessagesCountElement = document.getElementById('unread-messages-count');
    if (!unreadMessagesCountElement) {
        console.log('Message count element not found');
        return;
    }
    
    // Function to update the unread messages count
    function updateUnreadMessagesCount() {
        console.log('Checking for unread messages...');
        fetch('/messaging/unread-count')
            .then(response => response.json())
            .then(data => {
                console.log('Received count:', data.count);
                if (data.count > 0) {
                    // Show count
                    unreadMessagesCountElement.textContent = data.count;
                    unreadMessagesCountElement.style.display = 'inline-block';
                    console.log('Displaying badge with count:', data.count);
                } else {
                    // If no unread messages, hide the badge
                    unreadMessagesCountElement.style.display = 'none';
                    console.log('No unread messages, hiding badge');
                }
            })
            .catch(error => {
                console.error('Error fetching unread message count:', error);
                // Hide badge on error
                unreadMessagesCountElement.style.display = 'none';
            });
    }
    
    // Update count immediately and then every 30 seconds
    updateUnreadMessagesCount();
    setInterval(updateUnreadMessagesCount, 30000);
});
