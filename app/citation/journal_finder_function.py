@citation_bp.route('/journal-finder', methods=['GET', 'POST'])
@login_required
def journal_finder():
    """Journal finder route for premium users"""
    print("\n======= JOURNAL FINDER ROUTE ACCESSED =======\n")
    print(f"Request method: {request.method}")
    
    # Check if user is authenticated
    if not current_user.is_authenticated:
        flash('You need to log in to access this feature.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Check if user is premium (only premium users can access journal finder)
    # First find the RegisteredUser associated with the current user
    registered_user = db.session.query(RegisteredUser).filter_by(user_id=current_user.user_id).first()
    is_premium = False
    if registered_user:
        # Then check if this RegisteredUser has a premium profile
        is_premium = db.session.query(PremiumUser).filter_by(registered_user_id=registered_user.registered_user_id).first() is not None
    if not is_premium:
        print("User is not a premium user")
        return render_template('citations/journal_finder_premium_required.html')
    
    # Import required modules
    import os
    import json
    import re
    import string
    import time
    import traceback
    import numpy as np
    from collections import Counter
    from werkzeug.utils import secure_filename
    
    # Initialize variables for both GET and POST requests
    matching_journals = []
    submitted = False
    
    # Load journal data from JSON file
    journals = []
    try:
        # Simplify the path construction to avoid OSErrors on Windows
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        json_path = os.path.join(base_dir, 'journals.json')
        
        print(f"Loading journals from: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            journals = json.load(f)
        
        print(f"Loaded {len(journals)} journals successfully")
    except Exception as e:
        print(f"ERROR loading journals: {str(e)}")
        flash(f'Error loading journal data: {str(e)}. Please contact support.', 'danger')
        return render_template('citations/journal_finder.html', 
                              matching_journals=[], 
                              submitted=False)
                              
    if not journals:
        flash('No journals available in the database', 'warning')
        return render_template('citations/journal_finder.html', 
                              matching_journals=[], 
                              submitted=False)
    
    # Process the form if submitted
    if request.method == 'POST':
        submitted = True
        try:
            # Get form data
            title = request.form.get('title', '').strip()
            abstract = request.form.get('abstract', '').strip()
            open_access_only = request.form.get('open_access_only') == 'on'
            show_all = request.form.get('results_count') == 'all'
            
            # Handle file upload if present
            uploaded_file = request.files.get('paper_file')
            paper_text = ''
            
            if uploaded_file and uploaded_file.filename != '':
                try:
                    # Store the file temporarily
                    filename = secure_filename(uploaded_file.filename)
                    file_path = os.path.join('/tmp', filename)
                    uploaded_file.save(file_path)
                    
                    # Extract text from PDF if it's a PDF file
                    if filename.lower().endswith('.pdf'):
                        try:
                            import PyPDF2
                            with open(file_path, 'rb') as f:
                                pdf_reader = PyPDF2.PdfReader(f)
                                for page_num in range(len(pdf_reader.pages)):
                                    page = pdf_reader.pages[page_num]
                                    paper_text += page.extract_text() + ' '
                        except ImportError:
                            flash('PDF extraction library not available', 'warning')
                        except Exception as e:
                            flash(f'Error extracting text from PDF: {str(e)}', 'warning')
                    else:
                        # For non-PDF files, try reading as text
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                paper_text = f.read()
                        except UnicodeDecodeError:
                            flash('Unable to read the uploaded file. Please ensure it is a text file or PDF.', 'warning')
                        except Exception as e:
                            flash(f'Error reading file: {str(e)}', 'warning')
                    
                    # Clean up temporary file
                    try:
                        os.remove(file_path)
                    except:
                        pass
                except Exception as e:
                    flash(f'Error processing uploaded file: {str(e)}', 'warning')
            
            # Process paper content if we have at least one input source
            if title or abstract or paper_text:
                # Combine all available text
                paper_content = f"{title} {abstract} {paper_text}".strip()
                
                # Helper function to extract keywords (for fallback matching)
                def extract_keywords(text):
                    # Convert to lowercase and remove punctuation
                    text = text.lower()
                    for char in string.punctuation:
                        text = text.replace(char, ' ')
                    
                    # Split into words and remove common words
                    words = text.split()
                    stopwords = set(['and', 'the', 'is', 'in', 'to', 'of', 'a', 'for', 'with', 'on', 'as', 'by', 'that', 'this'])
                    keywords = [word for word in words if word not in stopwords and len(word) > 2]
                    
                    # Find most common words
                    word_counts = Counter(keywords)
                    return [word for word, count in word_counts.most_common(20)]
                
                try:
                    # Start measuring time for embedding generation
                    start_time = time.time()
                    
                    # Import NLP libraries
                    from sentence_transformers import SentenceTransformer
                    
                    # Helper functions for embeddings
                    def get_text_embedding(text, max_length=5000):
                        """Generate an embedding for the given text, with truncation for very long texts"""
                        # Safety check for empty text
                        if not text or len(text.strip()) == 0:
                            return np.zeros(384)
                        
                        # Truncate very long texts to avoid issues
                        if len(text) > max_length:
                            text = text[:max_length]
                        
                        try:
                            # Load model lazily (first time it's needed)
                            global model
                            if not 'model' in globals() or model is None:
                                model = SentenceTransformer('all-MiniLM-L6-v2')
                            
                            # Generate embedding
                            embedding = model.encode(text)
                            return embedding
                        except Exception as e:
                            print(f"ERROR generating embedding: {str(e)}")
                            traceback.print_exc()
                            return np.zeros(384)
                    
                    def cosine_similarity(v1, v2):
                        """Calculate cosine similarity between two vectors"""
                        dot_product = np.dot(v1, v2)
                        norm_v1 = np.linalg.norm(v1)
                        norm_v2 = np.linalg.norm(v2)
                        similarity = dot_product / (norm_v1 * norm_v2) if norm_v1 > 0 and norm_v2 > 0 else 0
                        return similarity
                    
                    # Get paper embedding
                    paper_embedding = get_text_embedding(paper_content)
                    
                    # Cache for journal embeddings
                    journal_embeddings = {}
                    
                    # Compute similarities for all journals
                    similarities = []
                    
                    for journal in journals:
                        # Only include open access journals if the filter is on
                        if open_access_only and not journal.get('open_access', False):
                            continue
                        
                        # Get journal description for semantic matching
                        journal_text = f"{journal.get('name', '')} {journal.get('description', '')} {journal.get('field', '')}"
                        
                        # Get embedding for journal (use cache if available)
                        if journal['name'] in journal_embeddings:
                            journal_embedding = journal_embeddings[journal['name']]
                        else:
                            journal_embedding = get_text_embedding(journal_text)
                            journal_embeddings[journal['name']] = journal_embedding
                        
                        # Compute similarity
                        similarity = cosine_similarity(paper_embedding, journal_embedding)
                        
                        # Add to results
                        similarities.append((journal, similarity))
                    
                    # Sort by similarity score (highest first)
                    similarities.sort(key=lambda x: x[1], reverse=True)
                    
                    # Process results with fallback mechanisms
                    matching_journal_tuples = []
                    threshold = 0.4  # Initial similarity threshold
                    
                    # First attempt: Use semantic similarity with default threshold
                    matching_journal_tuples = [(j, s) for j, s in similarities if s >= threshold]
                    
                    # First fallback: Lower the threshold
                    if not matching_journal_tuples:
                        threshold = 0.2  # Lower threshold
                        matching_journal_tuples = [(j, s) for j, s in similarities if s >= threshold]
                    
                    # Second fallback: Try keyword overlap matching
                    if not matching_journal_tuples:
                        # Extract keywords from the paper content
                        paper_keywords = set(extract_keywords(paper_content))
                        
                        # Match based on keyword overlap
                        keyword_matches = []
                        for journal, _ in similarities:
                            journal_text = f"{journal.get('name', '')} {journal.get('description', '')} {journal.get('field', '')}"
                            journal_keywords = set(extract_keywords(journal_text))
                            
                            # Calculate overlap
                            overlap = len(paper_keywords.intersection(journal_keywords)) / max(1, len(paper_keywords))
                            if overlap > 0:
                                keyword_matches.append((journal, overlap))
                        
                        # Sort by overlap
                        keyword_matches.sort(key=lambda x: x[1], reverse=True)
                        matching_journal_tuples = keyword_matches
                    
                    # Third fallback: Default to top journals by field similarity
                    if not matching_journal_tuples:
                        matching_journal_tuples = [(j, s) for j, s in similarities[:5]]
                        flash('No close matches found based on your paper. Showing top journals in your field.', 'info')
                    
                    # Format journal data properly for template display
                    matching_journals = []
                    for journal, score in matching_journal_tuples:
                        # Create a copy of the journal dict to avoid modifying the original
                        journal_copy = journal.copy()
                        
                        # Add the match score as a property (convert to percentage)
                        journal_copy['match_score'] = score
                        
                        # Ensure all required fields exist
                        if 'name' not in journal_copy:
                            journal_copy['name'] = 'Unknown Journal'
                        if 'field' not in journal_copy:
                            journal_copy['field'] = 'General'
                        if 'open_access' not in journal_copy:
                            journal_copy['open_access'] = False
                        if 'submit_link' not in journal_copy:
                            journal_copy['submit_link'] = '#'
                        if 'aims_scope_link' not in journal_copy:
                            journal_copy['aims_scope_link'] = '#'
                        
                        # Add to formatted results
                        matching_journals.append(journal_copy)
                    
                    # Limit results unless "show all" is selected
                    if not show_all and len(matching_journals) > 3:
                        matching_journals = matching_journals[:3]
                    
                    # Measure elapsed time
                    elapsed_time = time.time() - start_time
                    print(f"Journal matching completed in {elapsed_time:.2f}s")
                    
                except Exception as e:
                    print(f"Error in semantic matching: {str(e)}")
                    traceback.print_exc()
                    flash(f"Error matching journals: {str(e)}", 'danger')
            else:
                flash('Please provide a paper title, abstract, or upload a file.', 'warning')
        except Exception as e:
            print(f"Error processing form: {str(e)}")
            traceback.print_exc()
            flash(f"Error processing your request: {str(e)}", 'danger')
            submitted = False  # Don't show results on error
    
    # Render template with results
    return render_template('citations/journal_finder.html',
                          matching_journals=matching_journals,
                          submitted=submitted)
