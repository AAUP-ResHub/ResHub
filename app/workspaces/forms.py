from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Optional, Length

class UploadFileForm(FlaskForm):
    """Form for uploading files to workspaces or documents"""
    file = FileField('File', validators=[
        FileRequired('Please select a file')
    ])
    description = TextAreaField('Description (Optional)')
    submit = SubmitField('Upload File')


class InviteMemberForm(FlaskForm):
    """Form for inviting members to a workspace"""
    email_or_username = StringField('Email or Username', validators=[
        DataRequired('Please enter an email or username')
    ])
    role = SelectField('Role', choices=[
        ('viewer', 'Viewer'),
        ('editor', 'Editor'),
        ('admin', 'Admin')
    ], default='viewer')
    submit = SubmitField('Send Invitation')


class CreateDocumentForm(FlaskForm):
    """Form for creating a new document in a workspace"""
    title = StringField('Document Title', validators=[
        DataRequired('Please enter a document title'),
        Length(min=3, max=255)
    ])
    content = TextAreaField('Initial Content (Optional)')
    submit = SubmitField('Create Document')
