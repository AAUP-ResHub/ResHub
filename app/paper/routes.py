import os
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import desc

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
    
    # Only increment read_count if not the owner
    if current_user.is_authenticated:
        # Check if user has a registered profile before accessing its attributes
        has_profile = hasattr(current_user, 'registered_profile') and current_user.registered_profile is not None
        
        # Only compare user_id if user has a profile
        is_owner = False
        if has_profile:
            is_owner = current_user.registered_profile.registered_user_id == paper.owner_registered_user_id
            
        # Increment read count if not the owner
        if not is_owner and paper.metrics:
            paper.metrics.read_count += 1
            db.session.commit()
    
    return render_template('papers/paper_detail.html', paper=paper)

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
                
            # Get citation metadata fields
            authors = request.form.get('authors', '')
            publication_year = request.form.get('publication_year', '')
            journal = request.form.get('journal', '')
            volume = request.form.get('volume', '')
            issue = request.form.get('issue', '')
            pages = request.form.get('pages', '')
            publisher = request.form.get('publisher', '')
            doi = request.form.get('doi', '')
                
            # Create new paper record with citation metadata
            paper = ResearchPaper(
                title=title,
                abstract=abstract,
                file_path=db_file_path,
                keywords=keywords,
                owner_registered_user_id=current_user.registered_profile.registered_user_id,
                publish_date=datetime.utcnow(),
                # Citation metadata fields
                authors=authors,
                publication_year=publication_year,
                journal=journal,
                volume=volume,
                issue=issue,
                pages=pages,
                publisher=publisher,
                doi=doi
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
    paper = ResearchPaper.query.get_or_404(paper_id)
    
    # Only increment download count if not the owner
    # Check if user has a registered profile before accessing its attributes
    has_profile = hasattr(current_user, 'registered_profile') and current_user.registered_profile is not None
    
    # Only compare user_id if user has a profile
    is_owner = False
    if has_profile:
        is_owner = current_user.registered_profile.registered_user_id == paper.owner_registered_user_id
        
    # Increment download count if not the owner
    if paper.metrics and not is_owner:
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

@paper_bp.route('/<int:paper_id>/view-in-browser')
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

@paper_bp.route('/my-papers')
@login_required
def my_papers():
    """Display papers uploaded by the logged-in user"""
    # Check if user has a registered profile
    if not hasattr(current_user, 'registered_profile') or current_user.registered_profile is None:
        flash('You need to complete your profile before accessing your papers.', 'warning')
        return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    
    # Get the registered_user_id of the current user
    user_id = current_user.registered_profile.registered_user_id
    current_app.logger.info(f"Fetching papers for user_id: {user_id}")
    
    # Check all papers to see owner association
    all_papers = ResearchPaper.query.all()
    for paper in all_papers:
        current_app.logger.info(f"Paper ID: {paper.paper_id}, Title: {paper.title}, Owner ID: {paper.owner_registered_user_id}")
    
    # For papers where owner_registered_user_id is NULL, assign to current user
    orphaned_papers = ResearchPaper.query.filter_by(owner_registered_user_id=None).all()
    for paper in orphaned_papers:
        current_app.logger.info(f"Assigning orphaned paper '{paper.title}' to user {user_id}")
        paper.owner_registered_user_id = user_id
    
    if orphaned_papers:
        try:
            db.session.commit()
            flash(f"Found {len(orphaned_papers)} papers without an owner that were assigned to your account.", "info")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error assigning papers: {e}")
    
    # Now query papers owned by the current user
    papers = ResearchPaper.query.filter_by(owner_registered_user_id=user_id) \
        .order_by(desc(ResearchPaper.publish_date)) \
        .paginate(page=page, per_page=10, error_out=False)
    
    # Check if user is premium (for the "Find Best Journal" button)
    is_premium = current_user.has_premium
    
    return render_template('papers/my_papers.html', 
                           papers=papers,
                           title="My Research Papers",
                           is_premium=is_premium)

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
