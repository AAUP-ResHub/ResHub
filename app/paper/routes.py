import os
from flask import render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import desc
from flask_wtf import FlaskForm

from app.paper import paper_bp
from app.models import ResearchPaper, PaperMetrics, RegisteredUser
from app.extensions import db

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf'}

@paper_bp.route('/')
def index():
    """Display a list of all papers (paginated)"""
    page = request.args.get('page', 1, type=int)
    papers = ResearchPaper.query.order_by(desc(ResearchPaper.publish_date)).paginate(
        page=page, per_page=10, error_out=False)
    return render_template('papers/papers.html', papers=papers)

@paper_bp.route('/<int:paper_id>')
def paper_detail(paper_id):
    """Display detailed paper view"""
    paper = ResearchPaper.query.get_or_404(paper_id)
    form = FlaskForm()  # Create a form instance for CSRF token
    
    # Only increment read_count if not the owner
    if current_user.is_authenticated:
        if current_user.is_anonymous or current_user.registered_profile.registered_user_id != paper.owner_registered_user_id:
            if paper.metrics:
                paper.metrics.read_count += 1
                db.session.commit()
    
    return render_template('papers/paper_detail.html', paper=paper, form=form)

@paper_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_paper():
    """Upload a new paper"""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'paper_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['paper_file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        # Get form data
        title = request.form.get('title')
        abstract = request.form.get('abstract')
        keywords = request.form.get('keywords', '')
        
        if not title or not abstract:
            flash('Title and abstract are required', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Secure filename to prevent directory traversal
            filename = secure_filename(file.filename)
            
            # Generate unique filename using timestamp
            import time
            unique_filename = f"{int(time.time())}_{filename}"
            
            # Get the uploads folder
            uploads_dir = os.path.join(current_app.static_folder, 'uploads', 'papers')
            
            # Ensure the directory exists
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(uploads_dir, unique_filename)
            file.save(file_path)
            
            # Store relative path in database
            db_file_path = f"uploads/papers/{unique_filename}"
            
            # Check if user has a registered profile
            if not hasattr(current_user, 'registered_profile') or current_user.registered_profile is None:
                # Create a registered profile for the user if not exists
                registered_user = RegisteredUser(user_id=current_user.user_id)
                db.session.add(registered_user)
                db.session.commit()
                # Refresh the user object to get the new registered_profile
                db.session.refresh(current_user)
                
            # Create new paper record
            paper = ResearchPaper(
                title=title,
                abstract=abstract,
                file_path=db_file_path,
                keywords=keywords,
                owner_registered_user_id=current_user.registered_profile.registered_user_id
            )
            
            # Create metrics record
            metrics = PaperMetrics(
                read_count=0,
                download_count=0,
                citation_count=0
            )
            
            # Link paper and metrics
            paper.metrics = metrics
            
            # Save to database
            db.session.add(paper)
            db.session.commit()
            
            flash('Paper uploaded successfully!', 'success')
            return redirect(url_for('paper.paper_detail', paper_id=paper.paper_id))
        else:
            flash('Only PDF files are allowed', 'danger')
            
    return render_template('papers/upload_paper.html')

@paper_bp.route('/<int:paper_id>/download', methods=['GET', 'POST'])
@login_required
def download_paper(paper_id):
    """Download a paper (only for logged-in users)"""
    form = FlaskForm()
    if not form.validate_on_submit():
        return current_app.abort(400)  # Bad request if CSRF validation fails
        
    paper = ResearchPaper.query.get_or_404(paper_id)
    
    # Check if the paper has a file path
    if not paper.file_path:
        flash('This paper does not have an associated PDF file.', 'warning')
        return redirect(url_for('paper.paper_detail', paper_id=paper_id))
    
    # Only increment download count if not the owner
    if paper.metrics and current_user.registered_profile.registered_user_id != paper.owner_registered_user_id:
        paper.metrics.download_count += 1
        db.session.commit()
    
    # Extract filename from the path
    filename = os.path.basename(paper.file_path)
    
    # Get the directory part
    directory = os.path.join(current_app.static_folder, os.path.dirname(paper.file_path))
    
    # Create a more descriptive filename for download
    download_name = f"{paper.title.replace(' ', '_')}.pdf"
    
    # Set content headers to ensure proper download
    response = send_from_directory(
        directory, 
        filename, 
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )
    
    # Add extra headers to prevent IDM from intercepting
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@paper_bp.route('/<int:paper_id>/view-in-browser', methods=['GET'])
@login_required
def view_in_browser(paper_id):
    """View a paper PDF directly in a new browser tab (only for logged-in users)"""
    try:
        paper = ResearchPaper.query.get_or_404(paper_id)
        
        if not paper.file_path:
            flash('This paper does not have an associated PDF file.', 'warning')
            return redirect(url_for('paper.paper_detail', paper_id=paper_id))
        
        return redirect(url_for('static', filename=paper.file_path))
        
    except Exception as e:
        current_app.logger.error(f"Error viewing PDF: {str(e)}")
        flash('An error occurred while trying to view the PDF.', 'danger')
        return redirect(url_for('paper.paper_detail', paper_id=paper_id))

@paper_bp.route('/user/<int:user_id>')
def user_papers(user_id):
    """Display papers uploaded by a specific user"""
    page = request.args.get('page', 1, type=int)
    user = RegisteredUser.query.get_or_404(user_id)
    papers = ResearchPaper.query.filter_by(owner_registered_user_id=user_id) \
        .order_by(desc(ResearchPaper.publish_date)) \
        .paginate(page=page, per_page=10, error_out=False)
    
    return render_template('papers/papers.html', 
                           papers=papers, 
                           title=f"Papers by {user.user.username}")

@paper_bp.route('/search')
def search():
    """Redirect to the global search feature"""
    q = request.args.get('q', '')
    
    # Redirect to the global search endpoint
    if q:
        return redirect(url_for('search.results', q=q))
    else:
        # If no search query, just show all papers
        return redirect(url_for('paper.index'))
