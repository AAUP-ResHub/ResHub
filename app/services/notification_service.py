from flask import current_app
from app.extensions import db
from datetime import datetime
from app.models import User, RegisteredUser, Notification, CollaborationWorkspace as Workspace, WorkspaceFile

# Try importing forum models, use placeholders if not yet available
try:
    from app.models import ForumPost, ForumTopic
except ImportError:
    # Define placeholder classes if Forum models are not yet available
    # This allows the logic to be written without breaking if models are pending
    class ForumPost:  # Placeholder
        def __init__(self, post_id=None, content=None, author_registered_user_id=None, topic_id=None):
            self.post_id = post_id
            self.content = content
            self.author_registered_user_id = author_registered_user_id
            self.topic_id = topic_id

    class ForumTopic:  # Placeholder
        def __init__(self, topic_id=None, title=None):
            self.topic_id = topic_id
            self.title = title
    
    current_app.logger.warning("ForumPost or ForumTopic models not found. Using placeholders in notification_service.")


def _create_notification_record(recipient_id, actor_id, action, object_type=None, object_id=None, message=None):
    """
    Internal helper to create and save a notification record.
    
    Args:
        recipient_id: The registered_user_id of the notification recipient
        actor_id: The registered_user_id of the user performing the action (can be None for system)
        action: String identifying the type of notification (e.g., 'workspace_invite')
        object_type: String identifying the type of object related to the notification
        object_id: ID of the object related to the notification
        message: Human-readable message for the notification
        
    Returns:
        The created Notification object, or None if creation failed
    """
    # Create notification object - only use fields that exist in the model
    notification = Notification(
        recipient_registered_user_id=recipient_id,
        message=message or f"You have a new notification related to {action}"
        # sent_date will be set by default=datetime.utcnow in the model
        # is_read will be set by default=False in the model
    )
    
    # Store additional data in the message if needed
    if not message and (actor_id or action):
        actor_info = f" from user ID {actor_id}" if actor_id else ""
        notification.message = f"Action '{action}'{actor_info}: {object_type or ''} {object_id or ''}"
    
    db.session.add(notification)
    try:
        db.session.commit()
        current_app.logger.info(f"Notification created: Recipient {recipient_id}, Actor {actor_id}, Action {action}, Object {object_type}:{object_id if object_id else 'N/A'}")
        # TODO: Emit real-time event via SocketIO here for the recipient_id
        # Example: from app.socketio_handlers import emit_new_notification # (This file/function would be created later)
        #          emit_new_notification(notification.notification_id, recipient_id)
        return notification
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating notification for recipient {recipient_id}, action {action}: {e}")
        # Detailed error logging
        import traceback
        current_app.logger.error(f"Detailed traceback: {traceback.format_exc()}")
        return None


def generate_notification_message(action, actor, related_object=None, context_data=None):
    """
    Generates a human-readable message for a notification.
    
    Args:
        action: String identifying the type of notification
        actor: RegisteredUser object of the actor (can be None for system)
        related_object: The primary model instance related to this notification
        context_data: Optional dictionary with additional context for message generation
        
    Returns:
        A string with the human-readable notification message
    """
    actor_name = actor.user.username if actor and hasattr(actor, 'user') else "The system"
    message = f"Activity involving {actor_name} related to {action}."  # Default generic message

    if action == 'workspace_invite':
        if related_object and isinstance(related_object, Workspace):
            message = f"{actor_name} invited you to join the workspace: '{related_object.title}'."
    
    elif action == 'new_forum_reply':
        # related_object is the new ForumPost. context_data might contain the original post/topic.
        original_item_name = "a discussion"
        if context_data and 'topic' in context_data and hasattr(context_data['topic'], 'title'):
            original_item_name = f"the topic '{context_data['topic'].title}'"
        message = f"{actor_name} replied to {original_item_name}."
    
    elif action == 'new_file_in_workspace':
        if related_object and isinstance(related_object, WorkspaceFile):
            workspace_name = "a workspace"
            if context_data and 'workspace' in context_data:
                workspace = context_data['workspace']
                if hasattr(workspace, 'title'):
                    workspace_name = f"workspace '{workspace.title}'"
            file_name = related_object.filename if hasattr(related_object, 'filename') else "a file"
            message = f"{actor_name} uploaded {file_name} to {workspace_name}."
    
    elif action == 'user_mention':
        context = ""
        if context_data and 'snippet' in context_data:
            context = f" Context: '{context_data['snippet']}'"
        
        location = "a post"
        if related_object:
            if isinstance(related_object, ForumPost):
                location = "a forum post"
            elif isinstance(related_object, Workspace):
                location = f"workspace '{related_object.title}'"
            elif isinstance(related_object, WorkspaceFile):
                location = f"a file named '{related_object.filename}'"
        
        message = f"{actor_name} mentioned you in {location}.{context}"
    
    elif action == 'workspace_role_change':
        if context_data and 'workspace' in context_data and 'new_role' in context_data:
            workspace = context_data['workspace']
            workspace_name = workspace.title if hasattr(workspace, 'title') else "a workspace"
            new_role = context_data['new_role']
            message = f"{actor_name} changed your role to {new_role} in workspace '{workspace_name}'."
    
    # Add more action types and their message formats as needed
    
    return message


def send_notification(recipient_user, actor_user, action_key, related_object=None, context_data=None):
    """
    Primary public function to create and save a notification.
    
    Args:
        recipient_user: RegisteredUser object for the recipient
        actor_user: RegisteredUser object for the actor (can be None for system)
        action_key: String identifying the type of notification (e.g., 'workspace_invite')
        related_object: The primary model instance related to this notification
        context_data: Optional dictionary with additional context for message generation
        
    Returns:
        The created Notification object, or None if creation failed
    """
    # Validate inputs
    if not isinstance(recipient_user, RegisteredUser):
        current_app.logger.warning(f"Notification recipient is not a RegisteredUser: {type(recipient_user).__name__}")
        return None
    
    # Actor can be None for system notifications
    actor_id = None
    if actor_user:
        if not isinstance(actor_user, RegisteredUser):
            current_app.logger.warning(f"Notification actor is not a RegisteredUser: {type(actor_user).__name__}")
            return None
        actor_id = actor_user.registered_user_id

    # Generate human-readable message
    message = generate_notification_message(action_key, actor_user, related_object, context_data)
    
    # Determine object_type and object_id from the related_object
    object_type_val = None
    object_id_val = None
    if related_object:
        object_type_val = related_object.__class__.__name__
        if hasattr(related_object, 'workspace_id'):  # For Workspace
            object_id_val = related_object.workspace_id
        elif hasattr(related_object, 'file_id'):  # For WorkspaceFile
            object_id_val = related_object.file_id
        elif hasattr(related_object, 'post_id'):  # For ForumPost
            object_id_val = related_object.post_id
        elif hasattr(related_object, 'topic_id') and object_type_val == 'ForumTopic':  # For ForumTopic
            object_id_val = related_object.topic_id
        elif hasattr(related_object, 'paper_id'):  # For ResearchPaper
            object_id_val = related_object.paper_id
        elif hasattr(related_object, 'registered_user_id') and object_type_val == 'RegisteredUser':  # For a user being the object
            object_id_val = related_object.registered_user_id
        elif hasattr(related_object, 'id'):  # Generic fallback
            object_id_val = related_object.id
        else:
            current_app.logger.warning(f"Related object of type {object_type_val} does not have a recognized ID attribute for notification.")

    # Create the notification record with additional error handling
    try:
        return _create_notification_record(
            recipient_id=recipient_user.registered_user_id,
            actor_id=actor_id, 
            action=action_key,
            object_type=object_type_val,
            object_id=object_id_val,
            message=message
        )
    except Exception as e:
        current_app.logger.error(f"Unexpected error in send_notification: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        # Return None to indicate notification failed but don't halt the main workflow
        return None


# --- Specific Notification Helper Functions ---

def notify_workspace_invite(invited_user, workspace, inviting_user):
    """
    Sends a notification for a workspace invitation.
    
    Args:
        invited_user: RegisteredUser being invited
        workspace: Workspace being invited to
        inviting_user: RegisteredUser doing the inviting
        
    Returns:
        The created Notification object, or None if creation failed
    """
    try:
        if not all([invited_user, workspace, inviting_user]):
            current_app.logger.warning("Missing arguments for notify_workspace_invite.")
            return None
        
        # Verify all objects are of the correct type
        if not hasattr(invited_user, 'registered_user_id') or not hasattr(inviting_user, 'registered_user_id'):
            current_app.logger.warning("Invalid user objects provided to notify_workspace_invite.")
            return None
        
        if not hasattr(workspace, 'title') or not hasattr(workspace, 'workspace_id'):
            current_app.logger.warning("Invalid workspace object provided to notify_workspace_invite.")
            return None
            
        # Create a direct message string as a fallback
        direct_message = f"{inviting_user.user.username if hasattr(inviting_user, 'user') and hasattr(inviting_user.user, 'username') else 'Someone'} invited you to join workspace: '{workspace.title}'"
        
        return send_notification(
            recipient_user=invited_user,
            actor_user=inviting_user,
            action_key='workspace_invite',
            related_object=workspace
        )
    except Exception as e:
        current_app.logger.error(f"Error in notify_workspace_invite: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        # Don't propagate the error to the calling code
        return None


def notify_new_file_in_workspace(workspace, uploaded_file, uploader_user):
    """
    Notifies relevant workspace members about a new file.
    
    Args:
        workspace: The Workspace where file was uploaded
        uploaded_file: The WorkspaceFile that was uploaded
        uploader_user: RegisteredUser who uploaded the file
        
    Returns:
        True if notifications were attempted, False otherwise
    """
    if not all([workspace, uploaded_file, uploader_user]):
        current_app.logger.warning("Missing required arguments for new file notification.")
        return False

    if not isinstance(uploader_user, RegisteredUser):
        current_app.logger.warning(f"Uploader user is not a RegisteredUser: {type(uploader_user)}")
        return False
    
    # Get all member IDs at once to avoid N+1 queries
    member_ids = [assoc.user_id for assoc in workspace.members_in_workspace 
                  if assoc.user_id != uploader_user.registered_user_id]
    
    # Notify workspace owner if they're not the uploader
    if workspace.owner_id != uploader_user.registered_user_id:
        if workspace.owner_id in member_ids:
            # Owner is already in member_ids
            member_ids.remove(workspace.owner_id)
        
        owner_user = RegisteredUser.query.get(workspace.owner_id)
        if owner_user:
            send_notification(
                recipient_user=owner_user,
                actor_user=uploader_user,
                action_key='new_file_in_workspace',
                related_object=uploaded_file,
                context_data={'workspace': workspace}
            )

    # Bulk fetch all the users at once to avoid N+1 queries
    if member_ids:
        members = RegisteredUser.query.filter(RegisteredUser.registered_user_id.in_(member_ids)).all()
        for member in members:
            send_notification(
                recipient_user=member,
                actor_user=uploader_user,
                action_key='new_file_in_workspace',
                related_object=uploaded_file,
                context_data={'workspace': workspace}
            )
    
    return True


def notify_new_forum_reply(reply_author, original_post_author, topic_of_post, new_reply_post_object):
    """
    Notifies the author of an original post/topic when a new reply is made.
    
    Args:
        reply_author: RegisteredUser who wrote the new reply
        original_post_author: RegisteredUser to be notified (author of the parent post or topic starter)
        topic_of_post: The ForumTopic instance the reply belongs to
        new_reply_post_object: The new ForumPost instance (the reply itself)
        
    Returns:
        The created Notification object, or None if creation failed
    """
    if not all([reply_author, original_post_author, topic_of_post, new_reply_post_object]):
        current_app.logger.warning("Missing arguments for notify_new_forum_reply.")
        return None
    
    # Validate proper types
    if not isinstance(reply_author, RegisteredUser) or not isinstance(original_post_author, RegisteredUser):
        current_app.logger.warning("Forum reply notification requires RegisteredUser instances for authors.")
        return None
    
    # Avoid notifying someone about their own reply
    if reply_author.registered_user_id == original_post_author.registered_user_id:
        return None

    return send_notification(
        recipient_user=original_post_author,
        actor_user=reply_author,
        action_key='new_forum_reply',
        related_object=new_reply_post_object,
        context_data={'topic': topic_of_post}
    )


def notify_user_mention(mentioned_user, mentioning_user, content_object_where_mention_occurred, context_text_snippet=None):
    """
    Sends a notification when a user is mentioned.
    
    Args:
        mentioned_user: RegisteredUser who was mentioned
        mentioning_user: RegisteredUser who mentioned the user
        content_object_where_mention_occurred: The object where the mention occurred
        context_text_snippet: Optional text snippet showing the context of the mention
        
    Returns:
        The created Notification object, or None if creation failed
    """
    if not all([mentioned_user, mentioning_user, content_object_where_mention_occurred]):
        current_app.logger.warning("Missing arguments for notify_user_mention.")
        return None

    # Validate proper types
    if not isinstance(mentioned_user, RegisteredUser) or not isinstance(mentioning_user, RegisteredUser):
        current_app.logger.warning("User mention notification requires RegisteredUser instances.")
        return None

    # Don't notify users about their own mentions
    if mentioned_user.registered_user_id == mentioning_user.registered_user_id:
        return None

    context_data = {}
    if context_text_snippet:
        context_data['snippet'] = context_text_snippet

    return send_notification(
        recipient_user=mentioned_user,
        actor_user=mentioning_user,
        action_key='user_mention',
        related_object=content_object_where_mention_occurred,
        context_data=context_data
    )


# Function to parse text for @username mentions and trigger notifications.
# This would likely be called after content (e.g., forum post, workspace description) is saved.
def process_mentions_in_text(text_content, author_user, content_object):
    import re
    # Use regex to find patterns like @username in the text
    username_pattern = r'@(\w+)'
    usernames = re.findall(username_pattern, text_content)
    
    if usernames:
        for username in usernames:
            # Find the user by username
            user_obj = User.query.filter_by(username=username).first()
            if user_obj:
                # Get the registered user profile associated with this user
                registered_user = RegisteredUser.query.filter_by(user_id=user_obj.user_id).first()
                if registered_user and registered_user.registered_user_id != author_user.registered_user_id:
                    # Don't notify for self-mention
                    notify_user_mention(registered_user, author_user, content_object)
    return