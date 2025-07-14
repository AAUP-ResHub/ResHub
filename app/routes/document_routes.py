from flask import Blueprint, request, jsonify, current_app, render_template
from app.models import WorkspaceDocument as Document, db
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
import json

# Create a Blueprint for document routes
document_bp = Blueprint('document', __name__, url_prefix='/workspaces')

@document_bp.route('/document/<int:doc_id>', methods=['GET'])
@login_required
def view_document(doc_id):
    """View a document with the rich text editor."""
    try:
        # Get the document and verify access
        document = Document.query.get_or_404(doc_id)
        
        # Security check - verify the user has access to this document
        # Get the registered user profile linked to current user
        from app.models import RegisteredUser, WorkspaceMember, CollaborationWorkspace
        registered_user = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
        if not registered_user:
            return render_template('errors/error.html', code=404, message='User profile not found', description='Your user profile could not be found.'), 404
            
        # Check if user is a member of the workspace this document belongs to
        is_member = WorkspaceMember.query.filter_by(
            workspace_id=document.workspace_id,
            user_id=registered_user.registered_user_id
        ).first()
        if not is_member:
            return render_template('errors/error.html', code=403, message='Access Denied', description='You do not have permission to view this document.'), 403
        
        # Get the workspace to pass to the template (for breadcrumb navigation)
        workspace = CollaborationWorkspace.query.get(document.workspace_id)
        
        # Render the document editor template
        return render_template('workspaces/document_view.html', document=document, workspace=workspace)
        
    except Exception as e:
        # Log the error
        current_app.logger.error(f"Error viewing document {doc_id}: {str(e)}")
        return render_template('errors/error.html', code=500, message='Server Error', description=f'An error occurred while processing your request.'), 500

@document_bp.route('/document/<int:doc_id>/save', methods=['POST'])
@login_required
def save_document(doc_id):
    """Save document content via AJAX."""
    try:
        # Get the document and verify access
        document = Document.query.get_or_404(doc_id)
        
        # Security check - verify the user has access to this document
        # Get the registered user profile linked to current user
        from app.models import RegisteredUser
        registered_user = RegisteredUser.query.filter_by(user_id=current_user.user_id).first()
        if not registered_user:
            return jsonify({
                'status': 'error',
                'message': 'User profile not found'
            }), 404
            
        # Check if user is a member of the workspace this document belongs to
        # This is using the workspace_id directly from the document
        from app.models import WorkspaceMember
        is_member = WorkspaceMember.query.filter_by(
            workspace_id=document.workspace_id,
            user_id=registered_user.registered_user_id
        ).first()
        if not is_member:
            return jsonify({
                'status': 'error',
                'message': 'You do not have permission to edit this document'
            }), 403
        
        # Get content from JSON request
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No content provided'
            }), 400
        
        # Update document content
        document.content = data['content']
        
        # Save to database
        db.session.commit()
        
        # Return success response
        return jsonify({
            'status': 'success',
            'message': 'Document saved successfully'
        })
        
    except SQLAlchemyError as e:
        # Log the error
        current_app.logger.error(f"Database error saving document {doc_id}: {str(e)}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred'
        }), 500
    except Exception as e:
        # Log the error
        current_app.logger.error(f"Error saving document {doc_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}'
        }), 500
