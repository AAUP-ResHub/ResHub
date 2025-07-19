from flask_admin.contrib.sqla import ModelView
from flask import redirect, url_for, flash, request
from flask_login import current_user

class AdminModelView(ModelView):
    """Base class for all admin model views with admin-only access."""
    
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_type == 'admin'
        
    def inaccessible_callback(self, name, **kwargs):
        flash('You do not have permission to access the admin area.', 'error')
        return redirect(url_for('main.index'))
        
    # Common configuration for admin views
    can_view_details = True
    can_export = True
    page_size = 50

class UserModelView(AdminModelView):
    column_list = ('user_id', 'username', 'email', 'user_type', 'is_suspended')
    column_searchable_list = ('username', 'email')
    
    # Actions for user management
    can_create = True
    can_edit = True
    can_delete = True
    
    def on_model_change(self, form, model, is_created):
        # Check if password was provided on user creation
        if is_created and not model.password:
            model.set_password('defaultpassword')  # Set a default password if none provided

class RegisteredUserModelView(AdminModelView):
    column_list = ('registered_user_id', 'user.username', 'first_name', 'last_name')
    column_searchable_list = ('first_name', 'last_name', 'user.username')
    
    # Disable direct creation of registered user profiles
    can_create = False
    can_edit = True
    can_delete = True

class ForumPostModelView(AdminModelView):
    column_list = ('post_id', 'content', 'topic.title', 'author.user.username', 'timestamp', 'is_pinned')
    column_searchable_list = ('content',)
    column_editable_list = ('is_pinned',)
    
    # Forum post actions
    can_create = False  # Admin shouldn't create posts directly
    can_edit = True
    can_delete = True

class SiteSettingModelView(AdminModelView):
    """Admin view for site settings"""
    column_list = ('key', 'value', 'description')
    column_searchable_list = ('key', 'description')
    can_create = True
    can_edit = True
    can_delete = False  # Prevent deleting critical settings

class SystemLogView(AdminModelView):
    """View for system logs"""
    column_list = ('log_date', 'action')
    column_searchable_list = ('action',)
    can_create = False
    can_edit = False
    can_delete = False
    
    # Sort logs by timestamp descending by default
    column_default_sort = ('log_date', True)

class CollaborationWorkspaceModelView(AdminModelView):
    """View for managing collaboration workspaces"""
    column_list = ('workspace_id', 'title', 'owner_user.user.username', 'created_at')
    column_searchable_list = ('title',)
    
    # Allow full management of workspaces
    can_create = True
    can_edit = True
    can_delete = True

class WorkspaceDocumentModelView(AdminModelView):
    """View for managing workspace documents"""
    column_list = ('id', 'title', 'workspace.title', 'created_at')
    column_searchable_list = ('title',)
    
    # Allow full management of documents
    can_create = True
    can_edit = True
    can_delete = True

from flask_admin import BaseView, expose
from wtforms import Form, StringField, TextAreaField, validators

class AnnouncementView(BaseView):
    """Custom admin view for sending announcements to users"""
    @expose('/')
    def index(self):
        form = AnnouncementForm()
        return self.render('admin/announcement.html', form=form)
    
    @expose('/send', methods=['POST'])
    def send_announcement(self):
        form = AnnouncementForm(request.form)
        if form.validate():
            # Logic to send announcement would go here
            flash('Announcement sent successfully!', 'success')
            return redirect(url_for('.index'))
        return self.render('admin/announcement.html', form=form)
        
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_type == 'admin'

class AdminRegistrationView(BaseView):
    """Custom admin view for creating admin profiles"""
    @expose('/')
    def index(self):
        form = AdminRegistrationForm()
        return self.render('admin/admin_registration.html', form=form)
    
    @expose('/register', methods=['POST'])
    def register_admin(self):
        form = AdminRegistrationForm(request.form)
        if form.validate():
            # Logic to create admin user would go here
            flash('Admin user created successfully!', 'success')
            return redirect(url_for('.index'))
        return self.render('admin/admin_registration.html', form=form)
        
    def is_accessible(self):
        # Only superadmins should be able to create other admins
        return current_user.is_authenticated and current_user.user_type == 'superadmin'

# Forms for custom admin views
class AnnouncementForm(Form):
    title = StringField('Announcement Title', validators=[validators.DataRequired()])
    content = TextAreaField('Announcement Content', validators=[validators.DataRequired()])
    target_group = StringField('Target User Group (leave empty for all users)', validators=[validators.Optional()])

class AdminRegistrationForm(Form):
    username = StringField('Username', validators=[validators.DataRequired()])
    email = StringField('Email', validators=[validators.DataRequired(), validators.Email()])
    password = StringField('Password', validators=[validators.DataRequired()])
