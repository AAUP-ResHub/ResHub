from flask_admin.contrib.sqla import ModelView
from flask_admin import BaseView, expose
from flask_admin.actions import action
from flask import redirect, url_for, flash, request
from flask_login import current_user
from app.models import User, Admin, RegisteredUser
from werkzeug.security import generate_password_hash
from wtforms import Form, StringField, TextAreaField, validators
from app.extensions import db

class AdminModelView(ModelView):
    """Base class for all admin model views with admin-only access."""
    
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_type == 'admin'
        
    def inaccessible_callback(self, name, **kwargs):
        flash('You do not have permission to access the admin area.', 'error')
        return redirect(url_for('main.index'))
        
    # Common configuration for admin views
    can_view_details = False  # Hide view icons from all admin lists
    can_export = True
    page_size = 50

class UserModelView(AdminModelView):
    column_list = ('user_id', 'username', 'email', 'user_type', 'is_suspended')
    column_searchable_list = ('username', 'email')
    
    # Actions for user management
    can_create = True
    can_edit = True
    can_delete = True
    # can_view_details inherited from AdminModelView (set to False)
    
    # Custom formatting for the is_suspended column
    column_formatters = {
        'is_suspended': lambda v, c, m, p: 'Yes' if m.is_suspended else 'No'
    }
    
    def on_model_change(self, form, model, is_created):
        # Check if password was provided on user creation
        if is_created and not model.password:
            model.set_password('defaultpassword')  # Set a default password if none provided
    
    @action('suspend', 'Suspend User(s)', 'Are you sure you want to suspend the selected user(s)?')
    def action_suspend_users(self, ids):
        try:
            # Query users that are not already suspended
            users_to_suspend = User.query.filter(User.user_id.in_(ids), User.is_suspended == False).all()
            
            if not users_to_suspend:
                flash('No users were suspended (they may already be suspended)', 'warning')
                return
            
            # Suspend the users
            for user in users_to_suspend:
                user.is_suspended = True
            
            db.session.commit()
            
            count = len(users_to_suspend)
            flash(f'Successfully suspended {count} user(s)', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error suspending users: {str(e)}', 'error')
    
    @action('unsuspend', 'Unsuspend User(s)', 'Are you sure you want to unsuspend the selected user(s)?')
    def action_unsuspend_users(self, ids):
        try:
            # Query users that are currently suspended
            users_to_unsuspend = User.query.filter(User.user_id.in_(ids), User.is_suspended == True).all()
            
            if not users_to_unsuspend:
                flash('No users were unsuspended (they may already be active)', 'warning')
                return
            
            # Unsuspend the users
            for user in users_to_unsuspend:
                user.is_suspended = False
            
            db.session.commit()
            
            count = len(users_to_unsuspend)
            flash(f'Successfully unsuspended {count} user(s)', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error unsuspending users: {str(e)}', 'error')

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
    
    # Custom formatting for the is_pinned column
    column_formatters = {
        'is_pinned': lambda v, c, m, p: 'Yes' if m.is_pinned else 'No'
    }
    
    @action('pin', 'Pin Post(s)', 'Are you sure you want to pin the selected post(s)?')
    def action_pin_posts(self, ids):
        try:
            from app.models import ForumPost
            # Query posts that are not already pinned
            posts_to_pin = ForumPost.query.filter(ForumPost.post_id.in_(ids), ForumPost.is_pinned == False).all()
            
            if not posts_to_pin:
                flash('No posts were pinned (they may already be pinned)', 'warning')
                return
            
            # Pin the posts
            for post in posts_to_pin:
                post.is_pinned = True
            
            db.session.commit()
            
            count = len(posts_to_pin)
            flash(f'Successfully pinned {count} post(s)', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error pinning posts: {str(e)}', 'error')
    
    @action('unpin', 'Unpin Post(s)', 'Are you sure you want to unpin the selected post(s)?')
    def action_unpin_posts(self, ids):
        try:
            from app.models import ForumPost
            # Query posts that are currently pinned
            posts_to_unpin = ForumPost.query.filter(ForumPost.post_id.in_(ids), ForumPost.is_pinned == True).all()
            
            if not posts_to_unpin:
                flash('No posts were unpinned (they may already be unpinned)', 'warning')
                return
            
            # Unpin the posts
            for post in posts_to_unpin:
                post.is_pinned = False
            
            db.session.commit()
            
            count = len(posts_to_unpin)
            flash(f'Successfully unpinned {count} post(s)', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error unpinning posts: {str(e)}', 'error')

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

# Form classes

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
        return self.render('admin/create_admin.html', form=form)
    
    @expose('/register', methods=['POST'])
    def register_admin(self):
        form = AdminRegistrationForm(request.form)
        if form.validate():
            # Check if passwords match
            if form.password.data != form.confirm_password.data:
                return self.render('admin/create_admin.html', form=form, error="Passwords do not match")
                
            # Check if username already exists
            if User.query.filter_by(username=form.username.data).first():
                return self.render('admin/create_admin.html', form=form, error="Username already exists")
                
            # Check if email already exists
            if User.query.filter_by(email=form.email.data).first():
                return self.render('admin/create_admin.html', form=form, error="Email already exists")
                
            try:
                # Create new admin user
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    password_hash=generate_password_hash(form.password.data),
                    user_type='admin'
                )
                db.session.add(user)
                db.session.flush()  # Flush to get the user_id without committing
                
                # Create RegisteredUser profile (missing step that causes the integrity error)
                registered_user = RegisteredUser(user_id=user.user_id)
                db.session.add(registered_user)
                db.session.flush()
                
                # Create Admin profile
                admin = Admin(user_id=user.user_id)
                db.session.add(admin)
                db.session.commit()
                
                flash('Admin user created successfully!', 'success')
                return redirect(url_for('.index'))
            except Exception as e:
                db.session.rollback()
                return self.render('admin/create_admin.html', form=form, error=f"Error creating admin: {str(e)}")
                
        return self.render('admin/create_admin.html', form=form)
        
    def is_accessible(self):
        # Allow admins to create other admin profiles
        return current_user.is_authenticated and current_user.user_type == 'admin'

# Forms for custom admin views
class AnnouncementForm(Form):
    title = StringField('Announcement Title', validators=[validators.DataRequired()])
    content = TextAreaField('Announcement Content', validators=[validators.DataRequired()])
    target_group = StringField('Target User Group (leave empty for all users)', validators=[validators.Optional()])

class AdminRegistrationForm(Form):
    username = StringField('Username', validators=[validators.DataRequired()])
    email = StringField('Email', validators=[validators.DataRequired(), validators.Email()])
    password = StringField('Password', validators=[validators.DataRequired()])
    confirm_password = StringField('Confirm Password', validators=[validators.DataRequired()])
