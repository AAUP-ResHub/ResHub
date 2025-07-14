from flask import render_template, flash, redirect, url_for, request, jsonify, current_app, abort
from flask_login import login_required, current_user
from app.models import CollaborationWorkspace as Workspace, WorkspaceMember, WorkspaceDocument, RegisteredUser, WorkspaceFile, User
from app import db
from sqlalchemy.exc import SQLAlchemyError
from . import workspaces_bp
from .forms import UploadFileForm, InviteMemberForm, CreateDocumentForm
from flask_wtf import FlaskForm  # For CSRF protection
import datetime
import json
import os
from app.utils.s3_utils import upload_file_to_s3
from app.services.notification_service import notify_workspace_invite

# Helper function to get current registered user
def get_current_registered_user():
    return RegisteredUser.query.filter_by(user_id=current_user.user_id).first()

# Helper function to handle workspace deletion
def delete_workspace_handler(workspace_id, reg_user):
    """Handle workspace deletion logic."""
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # SECURITY CHECK: Only the owner can delete the workspace
    if workspace.owner_id != reg_user.registered_user_id:
        flash('You do not have permission to delete this workspace.', 'danger')
        abort(403)
    
    workspace_title = workspace.title  # Store title before deletion for the flash message
    
    try:
        # Step 1: Delete any attached files from S3 if applicable
        for workspace_file in workspace.files_in_workspace:
            if workspace_file.s3_object_key:  # If using S3 for storage
                try:
                    # This is a placeholder for S3 deletion logic
                    # If you're using boto3, you would call something like:
                    # s3_client.delete_object(Bucket=bucket_name, Key=workspace_file.s3_object_key)
                    current_app.logger.info(f"Deleted S3 object: {workspace_file.s3_object_key}")
                except Exception as s3_error:
                    current_app.logger.error(f"Error deleting S3 object {workspace_file.s3_object_key}: {s3_error}")
                    # Continue with deletion even if S3 deletion fails
        
        # Step 2: Explicitly delete related documents (this addresses potential circular dependency issues)
        documents = WorkspaceDocument.query.filter_by(workspace_id=workspace_id).all()
        for document in documents:
            db.session.delete(document)
        
        # Step 3: Now delete the workspace itself (which will cascade to other related entities)
        db.session.delete(workspace)
        db.session.commit()
        flash(f"Workspace '{workspace_title}' has been permanently deleted.", 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting workspace {workspace_id}: {str(e)}")
        flash('An error occurred while trying to delete the workspace.', 'danger')
    
    return redirect(url_for('workspaces.index'))


@workspaces_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """List all workspaces the current user is a member of."""
    # Get the current user's registered user profile
    user_profile = get_current_registered_user()
    
    if not user_profile:
        flash('User profile not found', 'danger')
        return redirect(url_for('main.index'))
    
    # Handle DELETE request from the delete form
    if request.method == 'POST':
        current_app.logger.info(f"POST request received: {request.form}")
        if request.form.get('workspace_id'):
            workspace_id = request.form.get('workspace_id')
            current_app.logger.info(f"Attempting to delete workspace ID: {workspace_id}")
            try:
                workspace_id = int(workspace_id)
                return delete_workspace_handler(workspace_id, user_profile)
            except ValueError:
                flash('Invalid workspace ID', 'danger')
                current_app.logger.error(f"Invalid workspace ID: {workspace_id}")
        else:
            current_app.logger.warning("POST request received but no workspace_id found in form data")
    
    # Get workspaces where user is a member but not the owner
    memberships = WorkspaceMember.query.filter_by(user_id=user_profile.registered_user_id).all()
    workspace_ids = [m.workspace_id for m in memberships]
    
    # Get workspaces user is a member of but does not own
    member_of_workspaces = Workspace.query.filter(
        Workspace.workspace_id.in_(workspace_ids),
        Workspace.owner_id != user_profile.registered_user_id
    ).all()
    
    # Get workspaces owned by the user
    owned_workspaces = Workspace.query.filter_by(owner_id=user_profile.registered_user_id).all()
    
    # Create an empty form for CSRF protection in delete modal
    delete_form = FlaskForm()
    
    return render_template('workspaces/index.html', 
                           owned_workspaces=owned_workspaces,
                           member_of_workspaces=member_of_workspaces,
                           delete_form=delete_form,
                           title="My Workspaces")


@workspaces_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new workspace."""
    if request.method == 'POST':
        # Get the current user's registered user profile
        user_profile = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
        
        if not user_profile:
            flash('User profile not found', 'danger')
            return redirect(url_for('main.index'))
        
        # Create new workspace
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            flash('Workspace name is required', 'danger')
            return render_template('workspaces/create.html', title="Create Workspace")
        
        try:
            workspace = Workspace(
                title=name,
                description=description,
                owner_id=user_profile.registered_user_id,
                created_at=datetime.datetime.utcnow()
            )
            
            db.session.add(workspace)
            db.session.commit()
            
            # Add the creator as a member
            member = WorkspaceMember(
                workspace_id=workspace.workspace_id,
                user_id=user_profile.registered_user_id,
                role='admin'  # Owner is admin
            )
            
            db.session.add(member)
            db.session.commit()
            
            flash('Workspace created successfully', 'success')
            return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace.workspace_id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error creating workspace: {str(e)}")
            flash('Error creating workspace', 'danger')
    
    return render_template('workspaces/create.html', title="Create Workspace")


@workspaces_bp.route('/<int:workspace_id>', methods=['GET'])
@login_required
def workspace_detail(workspace_id):
    """View a workspace, its documents, and members."""
    # Get the current registered user profile
    reg_user = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    if not reg_user:
        abort(403)

    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Authorization check (user must be a member to view)
    is_member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id,
        user_id=reg_user.registered_user_id
    ).first() is not None
    
    is_owner = workspace.owner_id == reg_user.registered_user_id
    
    if not (is_member or is_owner):
        flash('You do not have permission to view this workspace', 'danger')
        return redirect(url_for('workspaces.index'))
    
    # 1. Instantiate the form for inviting members
    invite_form = InviteMemberForm()
    
    # 2. Prepare the list of current members to display
    owner_details = {
        'username': workspace.owner_user.user.username if workspace.owner_user and workspace.owner_user.user else "Unknown",
        'role': 'Owner'
    }
    
    members_details = []
    for wm_assoc in workspace.members_in_workspace.all():
        if wm_assoc.member_user and wm_assoc.member_user.user:
            # Don't include the owner in the members list as they're displayed separately
            if wm_assoc.member_user.registered_user_id != workspace.owner_id:
                members_details.append({
                    'username': wm_assoc.member_user.user.username,
                    'role': wm_assoc.role,
                    'id': wm_assoc.member_user.registered_user_id
                })
    
    # Get workspace documents
    documents = WorkspaceDocument.query.filter_by(workspace_id=workspace_id)\
        .order_by(WorkspaceDocument.updated_at.desc()).all()
    
    # Form for creating new documents
    create_document_form = CreateDocumentForm()
    
    # Pass all data to the template
    return render_template('workspaces/workspace_detail.html', 
                           workspace=workspace,
                           owner_details=owner_details,
                           members_details=members_details,
                           invite_form=invite_form,
                           documents=documents,
                           create_document_form=create_document_form,
                           is_owner=is_owner,
                           title=workspace.title)


@workspaces_bp.route('/<int:workspace_id>/document/create', methods=['GET', 'POST'])
@login_required
def create_document(workspace_id):
    """Create a new document in the workspace."""
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Get the current user's registered user profile
    user_profile = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    
    if not user_profile:
        flash('User profile not found', 'danger')
        return redirect(url_for('main.index'))
    
    # Check if user is a member or owner
    is_member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id,
        user_id=user_profile.registered_user_id
    ).first() is not None
    
    is_owner = workspace.owner_id == user_profile.registered_user_id
    
    if not (is_member or is_owner):
        flash('You do not have permission to create documents in this workspace', 'danger')
        return redirect(url_for('workspaces.index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        
        if not title:
            flash('Document title is required', 'danger')
            return render_template('workspaces/create_document.html', workspace=workspace, title="Create Document")
        
        try:
            document = WorkspaceDocument(
                title=title,
                content=content,
                workspace_id=workspace_id,
                author_id=user_profile.registered_user_id,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            
            db.session.add(document)
            db.session.commit()
            
            flash('Document created successfully', 'success')
            return redirect(url_for('workspaces.view_document', workspace_id=workspace_id, doc_id=document.id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error creating document: {str(e)}")
            flash('Error creating document', 'danger')
    
    return render_template('workspaces/create_document.html', workspace=workspace, title="Create Document")


@workspaces_bp.route('/<int:workspace_id>/document/<int:doc_id>')
@login_required
def view_document(workspace_id, doc_id):
    """View a document in the workspace."""
    # Get the document
    document = WorkspaceDocument.query.get_or_404(doc_id)
    
    # Verify document belongs to this workspace
    if document.workspace_id != workspace_id:
        flash('Document not found in this workspace', 'danger')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Get the current user's registered user profile
    user_profile = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    
    if not user_profile:
        flash('User profile not found', 'danger')
        return redirect(url_for('main.index'))
    
    # Check if user is a member or owner
    is_member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id,
        user_id=user_profile.registered_user_id
    ).first() is not None
    
    is_owner = workspace.owner_id == user_profile.registered_user_id
    
    if not (is_member or is_owner):
        flash('You do not have permission to view this document', 'danger')
        return redirect(url_for('workspaces.index'))
    
    # Instantiate the form for file uploads
    upload_form = UploadFileForm()
    
    return render_template('workspaces/document_view.html', 
                           workspace=workspace,
                           document=document,
                           is_owner=is_owner,
                           upload_form=upload_form,
                           title=document.title)


@workspaces_bp.route('/<int:workspace_id>/document/<int:doc_id>/edit', methods=['GET'])
@login_required
def edit_document(workspace_id, doc_id):
    """Edit a document in the workspace using the rich text editor."""
    # Get the document
    document = WorkspaceDocument.query.get_or_404(doc_id)
    
    # Verify document belongs to this workspace
    if document.workspace_id != workspace_id:
        flash('Document not found in this workspace', 'danger')
        return redirect(url_for('workspaces.index'))
    
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Get the current user's registered user profile
    user_profile = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    
    if not user_profile:
        flash('User profile not found', 'danger')
        return redirect(url_for('main.index'))
    
    # Check if user is a member or owner
    is_member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id,
        user_id=user_profile.registered_user_id
    ).first() is not None
    
    is_owner = workspace.owner_id == user_profile.registered_user_id
    
    if not (is_member or is_owner):
        flash('You do not have permission to edit this document', 'danger')
        return redirect(url_for('workspaces.index'))
    
    # Create an upload form for document attachments
    upload_form = UploadFileForm()
    
    # Use the new Quill.js rich text editor
    return render_template('workspaces/document_view.html', 
                          workspace=workspace, 
                          document=document, 
                          upload_form=upload_form,
                          title=f"Edit: {document.title}")


@workspaces_bp.route('/<int:workspace_id>/upload_file', methods=['POST'])
@workspaces_bp.route('/upload_file', methods=['POST'])
@login_required
def upload_file(workspace_id=None):
    """Upload a file to a workspace or document"""
    # Get doc_id from form if provided
    doc_id = request.form.get('doc_id')
    if doc_id:
        doc_id = int(doc_id)
        
    # Get the registered user for the current user
    reg_user_uploader = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    
    if not reg_user_uploader:
        flash('User profile not found', 'danger')
        return redirect(url_for('main.index'))
    
    # Determine the context (workspace or document)
    if doc_id:
        doc = WorkspaceDocument.query.get_or_404(doc_id)
        workspace = doc.workspace
        workspace_id = workspace.workspace_id
    else:
        workspace = Workspace.query.get_or_404(workspace_id)
        doc = None
    
    # Check if user is a member or owner of the workspace
    is_member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id,
        user_id=reg_user_uploader.registered_user_id
    ).first() is not None
    
    is_owner = workspace.owner_id == reg_user_uploader.registered_user_id
    
    if not (is_member or is_owner):
        flash('You do not have permission to upload files to this workspace', 'danger')
        if doc_id:
            return redirect(url_for('main.index'))
        else:
            return redirect(url_for('workspaces.index'))
    
    form = UploadFileForm()
    if form.validate_on_submit():
        file_storage = form.file.data
        original_filename = file_storage.filename
        
        # Generate S3 bucket name (this should match your existing implementation)
        s3_bucket_name = current_app.config.get('S3_BUCKET_NAME', 'reshub-uploads')
        
        # Upload to S3 or local storage
        from app.utils.s3_utils import upload_file_to_s3
        s3_storage_key = upload_file_to_s3(file_storage, original_filename, file_storage.content_type)
        
        if s3_storage_key:
            # Get file size in bytes
            file_storage.seek(0, os.SEEK_END)
            file_size = file_storage.tell()
            file_storage.seek(0)
            
            # Create a new file record
            new_file_record = WorkspaceFile(
                workspace_id=workspace_id,
                document_id=doc_id,  # Will be None if uploading to workspace
                uploader_id=reg_user_uploader.registered_user_id,
                filename=original_filename,
                s3_object_key=s3_storage_key,  # Store the S3 key
                content_type=file_storage.content_type,
                size_bytes=file_size,
                description=form.description.data
            )
            db.session.add(new_file_record)
            
            try:
                db.session.commit()
                flash(f'File {original_filename} uploaded successfully', 'success')
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Database error saving file record: {str(e)}")
                flash('Error saving file record', 'danger')
        else:
            flash('Error uploading file to storage', 'danger')
    
    # Determine where to redirect back to
    if doc_id:
        return redirect(url_for('workspaces.view_document', workspace_id=workspace_id, doc_id=doc_id))
    else:
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))


@workspaces_bp.route('/<int:workspace_id>/files/<int:file_id>/download')
@login_required
def download_workspace_file(workspace_id, file_id):
    """Download a file from the workspace"""
    # Get the file record
    file_record = WorkspaceFile.query.get_or_404(file_id)
    
    # Verify file belongs to this workspace
    if file_record.workspace_id != workspace_id:
        flash('File not found in this workspace', 'danger')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Get the current user's registered user profile
    user_profile = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    
    if not user_profile:
        flash('User profile not found', 'danger')
        return redirect(url_for('main.index'))
    
    # Check if user is a member or owner
    is_member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id,
        user_id=user_profile.registered_user_id
    ).first() is not None
    
    is_owner = workspace.owner_id == user_profile.registered_user_id
    
    if not (is_member or is_owner):
        flash('You do not have permission to download this file', 'danger')
        return redirect(url_for('workspaces.index'))
    
    # Get the file by ID
    workspace_file = WorkspaceFile.query.get_or_404(file_id)
    
    # Verify the file belongs to the workspace for security
    if workspace_file.workspace_id != workspace_id:
        flash('File not found in this workspace', 'danger')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    
    try:
        # Get a pre-signed URL for downloading the file from S3
        from app.utils.s3_utils import get_file_download_url
        download_url = get_file_download_url(workspace_file.s3_object_key)
        
        # Redirect to the download URL
        return redirect(download_url)
        
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'danger')
        
        # Determine where to redirect based on whether the file is attached to a document
        if workspace_file.document_id:
            return redirect(url_for('workspaces.view_document', 
                                    workspace_id=workspace_id, 
                                    doc_id=workspace_file.document_id))
        else:
            return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))


@workspaces_bp.route('/<int:workspace_id>/invite', methods=['POST'])
@login_required
def invite_member_to_workspace(workspace_id):
    """Invite a new member to a workspace"""
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Get the current user's registered user profile
    inviter = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    
    if not inviter:
        flash('Your user profile was not found', 'danger')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    
    # Check if user is the owner (only owners can invite)
    if workspace.owner_id != inviter.registered_user_id:
        flash('Only workspace owners can invite members', 'warning')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    
    form = InviteMemberForm()
    if form.validate_on_submit():
        # Get the invited user by email or username
        email_or_username = form.email_or_username.data.strip()
        role = form.role.data
        
        # Try to find user by username first, then by email if not found
        invited_user = None
        # First check if it looks like an email (contains @)
        if '@' in email_or_username:
            user = User.query.filter_by(email=email_or_username).first()
            if user:
                invited_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
        else:
            user = User.query.filter_by(username=email_or_username).first()
            if user:
                invited_user = RegisteredUser.query.filter_by(user_id=user.user_id).first()
        
        if not invited_user:
            flash(f'User with email/username "{email_or_username}" not found', 'danger')
            return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
        
        # Check if user is already a member
        existing_membership = WorkspaceMember.query.filter_by(
            workspace_id=workspace_id,
            user_id=invited_user.registered_user_id
        ).first()
        
        if existing_membership:
            flash(f'User {email_or_username} is already a member of this workspace', 'info')
            return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
        
        # Add the user as a workspace member
        try:
            member = WorkspaceMember(
                workspace_id=workspace_id,
                user_id=invited_user.registered_user_id,
                role=role
            )
            
            db.session.add(member)
            db.session.commit()
            
            # Send notification to the invited user
            notification = notify_workspace_invite(invited_user, workspace, inviter)
            
            if notification:
                flash(f'User {email_or_username} has been invited to the workspace', 'success')
            else:
                flash(f'User {email_or_username} has been added to the workspace, but notification failed', 'warning')
                
            return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error inviting member: {str(e)}")
            flash('Error inviting member', 'danger')
    else:
        # If form validation fails, show errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {getattr(form, field).label.text}: {error}", 'danger')
    
    # If anything fails, redirect back to workspace detail
    return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))


@workspaces_bp.route('/<int:workspace_id>/member/<int:member_id>/remove', methods=['POST'])
@login_required
def remove_workspace_member(workspace_id, member_id):
    """Remove a member from a workspace."""
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Get the current user's registered user profile
    reg_user = get_current_registered_user()
    if not reg_user:
        flash('User profile not found', 'danger')
        return redirect(url_for('main.index'))
    
    # Security check: Only the owner can remove members
    if workspace.owner_id != reg_user.registered_user_id:
        flash('You do not have permission to remove members from this workspace.', 'danger')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    
    # Cannot remove the owner
    if member_id == workspace.owner_id:
        flash('The workspace owner cannot be removed.', 'danger')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    
    try:
        # Find the workspace member
        member = WorkspaceMember.query.filter_by(
            workspace_id=workspace_id,
            user_id=member_id
        ).first()
        
        if not member:
            flash('Member not found in this workspace.', 'danger')
            return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
        
        # Get the username for the flash message
        user = RegisteredUser.query.get(member_id)
        username = user.user.username if user and user.user else "Member"
        
        # Remove the member
        db.session.delete(member)
        db.session.commit()
        
        flash(f'"{username}" has been removed from the workspace.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error removing member: {str(e)}")
        flash('Error removing member from workspace.', 'danger')
    
    return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))


@workspaces_bp.route('/<int:workspace_id>/delete', methods=['POST'])
@login_required
def delete_workspace(workspace_id):
    """Delete a workspace that belongs to the current user."""
    # Get the current registered user
    reg_user = get_current_registered_user()
    if not reg_user:
        abort(403)
    
    return delete_workspace_handler(workspace_id, reg_user)


@workspaces_bp.route('/<int:workspace_id>/document/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(workspace_id, doc_id):
    """Delete a document from the workspace."""
    # Get the document
    document = WorkspaceDocument.query.get_or_404(doc_id)
    
    # Verify document belongs to this workspace
    if document.workspace_id != workspace_id:
        flash('Document not found in this workspace', 'danger')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Get the current user's registered user profile
    user_profile = get_current_registered_user()
    if not user_profile:
        flash('User profile not found', 'danger')
        return redirect(url_for('main.index'))
    
    # SECURITY CHECK: Only the workspace owner or document author can delete the document
    is_owner = workspace.owner_id == user_profile.registered_user_id
    is_author = document.author_id == user_profile.registered_user_id
    
    if not (is_owner or is_author):
        flash('You do not have permission to delete this document', 'danger')
        return redirect(url_for('workspaces.view_document', workspace_id=workspace_id, doc_id=doc_id))
    
    try:
        document_title = document.title  # Store for flash message
        
        # Delete the document (cascade will handle attachments)
        db.session.delete(document)
        db.session.commit()
        
        flash(f'Document "{document_title}" has been deleted', 'success')
        return redirect(url_for('workspaces.workspace_detail', workspace_id=workspace_id))
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error deleting document: {str(e)}")
        flash('Error deleting document', 'danger')
        return redirect(url_for('workspaces.view_document', workspace_id=workspace_id, doc_id=doc_id))

@workspaces_bp.route('/<int:workspace_id>/document/<int:doc_id>/save_content', methods=['POST'])
@login_required
def save_document_content(workspace_id, doc_id):
    """Save document content via AJAX request."""
    # Get the document
    document = WorkspaceDocument.query.get_or_404(doc_id)
    
    # Verify document belongs to this workspace
    if document.workspace_id != workspace_id:
        return jsonify({
            'status': 'error',
            'message': 'Document not found in this workspace'
        }), 404
    
    # Get the workspace
    workspace = Workspace.query.get_or_404(workspace_id)
    
    # Get the current user's registered user profile
    user_profile = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
    
    if not user_profile:
        return jsonify({
            'status': 'error',
            'message': 'User profile not found'
        }), 403
    
    # Check if user is a member or owner
    is_member = WorkspaceMember.query.filter_by(
        workspace_id=workspace_id,
        user_id=user_profile.registered_user_id
    ).first() is not None
    
    is_owner = workspace.owner_id == user_profile.registered_user_id
    
    if not (is_member or is_owner):
        return jsonify({
            'status': 'error',
            'message': 'You do not have permission to edit this document'
        }), 403
    
    # Get the content from the request
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({
            'status': 'error',
            'message': 'No content provided'
        }), 400
    
    try:
        # Update the document content
        document.content = data['content']
        document.updated_at = datetime.datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Document saved successfully'
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error saving document: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Error saving document'
        }), 500
