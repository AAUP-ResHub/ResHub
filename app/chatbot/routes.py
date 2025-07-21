from flask import render_template, request, jsonify, current_app, url_for, flash, Response, session, redirect
from flask_login import login_required, current_user
from app import db
from app.chatbot import chatbot_bp
from app.models import ChatLog, IndexedDocument, ChatSession, FeedbackDetail
from app.chatbot.vector_store import VectorStore
from app.chatbot.answer_generator import AnswerGenerator
from app.chatbot.pdf_processor import PDFProcessor
from app.chatbot.api_fetchers import ArxivFetcher, SemanticScholarFetcher, CoreFetcher
import time
import json
import os
import csv
import io
import requests
from datetime import datetime
from functools import wraps

# Error codes and messages for API responses
ERROR_CODES = {
    'rate_limit_exceeded': 'API rate limit exceeded. Please try again later.',
    'missing_api_key': 'API key is missing or invalid.',
    'paper_not_found': 'The requested paper could not be found.',
    'invalid_input': 'Invalid input parameters.',
    'server_error': 'An unexpected error occurred while processing your request.'
}

# Initialize components
vector_store = VectorStore()
pdf_processor = PDFProcessor()
answer_generator = AnswerGenerator()

# Test page for new frontend components
@chatbot_bp.route('/test')
@login_required 
def test_frontend():
    """Render the test page for new chatbot frontend components."""
    return render_template('chatbot_test.html')

# Main chatbot interface
@chatbot_bp.route('/')
@login_required
def index():
    """Render the chatbot interface."""
    # Get current user's registered profile
    if not current_user.registered_profile:
        flash('User profile not found. Please complete your registration.', 'error')
        return redirect(url_for('main.dashboard'))
    
    registered_user_id = current_user.registered_profile.registered_user_id
    
    # Get active session or create a new one
    active_session = ChatSession.query.filter_by(registered_user_id=registered_user_id, is_active=True).first()
    
    if not active_session:
        active_session = ChatSession(registered_user_id=registered_user_id)
        db.session.add(active_session)
        db.session.commit()
    
    # Get chat history for this session
    chat_history = ChatLog.query.filter_by(
        registered_user_id=registered_user_id, 
        session_id=active_session.session_id
    ).order_by(ChatLog.timestamp.desc()).limit(10).all()
    
    # Check if new UI feature flag is enabled
    from app.chatbot.feature_flags import get_feature_flags
    feature_flags = get_feature_flags()
    use_new_ui = feature_flags.get('USE_NEW_CHATBOT_UI', False)
    
    template = 'chatbot/chatbot_template.html' if use_new_ui else 'chatbot/index.html'
    
    return render_template(template, 
                          active_session=active_session,
                          chat_history=chat_history,
                          feature_flags=feature_flags)


# Public chatbot interface - no login required
@chatbot_bp.route('/public')
def public_chatbot():
    """Render the chatbot interface without authentication requirement."""
    # Create a dummy session for public access
    active_session = {'session_id': 'public-session'}
    chat_history = []
    
    # Check if new UI feature flag is enabled
    from app.chatbot.feature_flags import get_feature_flags
    feature_flags = get_feature_flags()
    use_new_ui = feature_flags.get('USE_NEW_CHATBOT_UI', False)
    
    template = 'chatbot/chatbot_template.html' if use_new_ui else 'chatbot/index.html'
    
    return render_template(template, 
                          active_session=active_session,
                          chat_history=chat_history,
                          feature_flags=feature_flags)

# API endpoint for chat
@chatbot_bp.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """Handle chat API requests."""
    data = request.json
    user_prompt = data.get('prompt', '')
    year_filter = data.get('years', None)
    citation_style = data.get('style', 'APA')
    session_id = data.get('session_id', None)
    
    if not user_prompt:
        return jsonify({"error": "Missing prompt"}), 400
    
    start_time = time.time()
    
    try:
        # Get current user's registered profile
        if not current_user.registered_profile:
            return jsonify({"error": "User profile not found. Please complete your registration."}), 400
        
        registered_user_id = current_user.registered_profile.registered_user_id
        
        # Get or create session for the current user
        current_app.logger.info(f"[SESSION DEBUG] Request with session_id={session_id}")
        
        if session_id:
            # Validate session ownership
            active_session = ChatSession.query.filter_by(session_id=session_id).first()
            if not active_session:
                current_app.logger.error(f"[SESSION DEBUG] Session {session_id} not found in database")
                return jsonify({"error": "Session not found"}), 404
            elif active_session.registered_user_id != registered_user_id:
                current_app.logger.error(f"[SESSION DEBUG] Session {session_id} belongs to user {active_session.registered_user_id}, not {registered_user_id}")
                return jsonify({"error": "Access denied"}), 403
            current_app.logger.info(f"[SESSION DEBUG] Using existing session {session_id} for user {registered_user_id}")
        else:
            # Create a new session with proper error handling
            try:
                title = "Chat session " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                active_session = ChatSession(registered_user_id=registered_user_id, title=title)
                db.session.add(active_session)
                db.session.commit()
            except Exception as e:
                db.session.rollback()  # Clear the failed transaction
                current_app.logger.error(f"[SESSION DEBUG] Failed to create ChatSession: {str(e)}")
                return jsonify({"error": "Failed to create chat session. Please try again."}), 500
            
            # Get the newly created session's ID
            session_id = active_session.session_id
            current_app.logger.info(f"[SESSION DEBUG] Created new session {session_id} for user {registered_user_id}, committed to DB")
            
            # Verify session exists in database after commit
            verification = ChatSession.query.get(session_id)
            if verification:
                current_app.logger.info(f"[SESSION DEBUG] Successfully verified new session {session_id} exists in database")
            else:
                current_app.logger.error(f"[SESSION DEBUG] Failed to verify new session {session_id} in database after commit!")
                # Try a second commit if verification failed
                try:
                    db.session.commit()
                    current_app.logger.info(f"[SESSION DEBUG] Attempted secondary commit for session {session_id}")
                except Exception as e:
                    current_app.logger.error(f"[SESSION DEBUG] Secondary commit failed: {str(e)}")

        # Re-fetch session to ensure we're using the latest from the database
        active_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not active_session:
            current_app.logger.error(f"[SESSION DEBUG] Critical: Session {session_id} not found after creation/validation")
            return jsonify({"error": "Session not found or creation failed"}), 500
        
        # 1. Search vector store for relevant chunks
        chunks = vector_store.search(user_prompt, limit=20)
        retrieved_ids = [chunk.get('id') for chunk in chunks]
        hit_rate = len(chunks) / 20 if chunks else 0  # Simple hit rate calculation
        
        # If no results, return a message
        if not chunks:
            result = {
                "answer": "I couldn't find any relevant research papers for your query.",
                "extras": "Please try a different question or adjust your search terms.",
                "citations": ""
            }
            token_in = len(user_prompt) // 4  # Approximate
            token_out = 20  # Approximate
        else:
            # 2. Generate answer based on retrieved chunks
            result = answer_generator.generate(
                query=user_prompt,
                chunks=chunks,
                citation_style=citation_style,
                max_tokens=500
            )
            token_in = result.get('token_in', len(user_prompt) // 4)
            token_out = result.get('token_out', 100)
        
        # 3. Log the chat
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        chat_log = ChatLog(
            registered_user_id=registered_user_id,
            session_id=session_id,
            user_prompt=user_prompt,
            ai_response=json.dumps(result),  # Store the full response
            token_in=token_in,
            token_out=token_out,
            latency_ms=latency_ms,
            hit_rate=hit_rate
        )
        chat_log.set_retrieved_ids(retrieved_ids)
        
        db.session.add(chat_log)
        db.session.commit()
        
        # Update the ChatSession last_active timestamp
        chat_session = ChatSession.query.get(session_id)
        chat_session.last_active = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "answer": result.get('answer', ''),
            "extras": result.get('extras', ''),
            "citations": result.get('citations', ''),
            "chat_id": chat_log.log_id,
            "session_id": session_id
        })
        
    except Exception as e:
        current_app.logger.error(f"Chat API error: {str(e)}")
        return jsonify({
            "error": "An error occurred processing your request.",
            "details": str(e)
        }), 500

# Test API endpoint for chat (no auth)
@chatbot_bp.route('/api/chat/test', methods=['POST'])
def chat_api_test():
    """Handle chat API requests without authentication for testing."""
    data = request.json
    user_prompt = data.get('prompt', '')
    citation_style = data.get('style', 'APA')
    session_id = data.get('session_id', None)
    
    if not user_prompt:
        return jsonify({"error": "Missing prompt"}), 400
    
    start_time = time.time()
    
    try:
        # Get or create a session (similar to authenticated endpoint)
        if not session_id:
            # Create a new test session
            user_id = session.get('_user_id', 'test-user')  # Use session user_id or fallback
            new_session = ChatSession(user_id=user_id, title="Test Session")
            db.session.add(new_session)
            db.session.commit()
            session_id = new_session.session_id
            
        # 1. Search vector store for relevant chunks
        chunks = vector_store.search(user_prompt, limit=20)
        retrieved_ids = [chunk.get('id') for chunk in chunks]
        hit_rate = len(chunks) / 20 if chunks else 0  # Simple hit rate calculation
        
        # If no results, return a message
        if not chunks:
            result = {
                "answer": "I couldn't find any relevant research papers for your query.",
                "extras": "Please try a different question or adjust your search terms.",
                "citations": ""
            }
            token_in = len(user_prompt) // 4  # Approximate
            token_out = 20  # Approximate
        else:
            # 2. Generate answer based on retrieved chunks
            result = answer_generator.generate(
                query=user_prompt,
                chunks=chunks,
                citation_style=citation_style,
                max_tokens=500
            )
            token_in = result.get('token_in', len(user_prompt) // 4)
            token_out = result.get('token_out', 100)
        
        # 3. Calculate latency and save to database
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        # Save chat log to database - this was missing before
        try:
            # Use test-user ID if not authenticated
            user_id = session.get('_user_id', 'test-user')
            
            # Create a new chat log
            chat_log = ChatLog(
                user_id=user_id,
                session_id=session_id,
                user_prompt=user_prompt,
                ai_response=result.get('answer', ''),  # Store the answer
                token_in=token_in,
                token_out=token_out,
                latency_ms=latency_ms
            )
            
            # Add and commit to database
            db.session.add(chat_log)
            db.session.commit()
            current_app.logger.info(f"Created chat log for test API with ID {chat_log.log_id}")
        except Exception as log_err:
            current_app.logger.error(f"Error saving chat log in test API: {str(log_err)}")
        
        # Update the session's last_active timestamp
        if session_id:
            try:
                chat_session = ChatSession.query.get(session_id)
                if chat_session:
                    chat_session.last_active = datetime.utcnow()
                    db.session.commit()
            except Exception as session_err:
                current_app.logger.error(f"Error updating session timestamp: {str(session_err)}")
        
        return jsonify({
            "answer": result.get('answer', ''),
            "extras": result.get('extras', ''),
            "citations": result.get('citations', ''),
            "test_mode": True,
            "latency_ms": latency_ms,
            "session_id": session_id,
            "chat_id": chat_log.log_id if 'chat_log' in locals() else None
        })
        
    except Exception as e:
        current_app.logger.error(f"Chat Test API error: {str(e)}")
        return jsonify({
            "error": "An error occurred processing your request.",
            "details": str(e)
        }), 500

# API endpoint for updating a specific session
@chatbot_bp.route('/api/chat/sessions/<session_id>', methods=['PATCH'])
@login_required
def update_session_api(session_id):
    """Update a specific chat session."""
    try:
        if not current_user.registered_profile:
            return jsonify({"error": "User profile not found"}), 404
        
        registered_user_id = current_user.registered_profile.registered_user_id
        
        # Verify session exists and belongs to user
        session = ChatSession.query.filter_by(
            session_id=session_id,
            registered_user_id=registered_user_id
        ).first()
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        data = request.json or {}
        
        # Update title if provided
        if 'title' in data:
            session.title = data['title']
            db.session.commit()
            
            return jsonify({
                "session_id": session.session_id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
                "is_active": session.is_active
            })
        
        return jsonify({"error": "No update data provided"}), 400
        
    except Exception as e:
        current_app.logger.error(f"Update Session API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API endpoint for chat sessions
@chatbot_bp.route('/api/chat/sessions', methods=['GET', 'POST'])
@login_required
def chat_sessions_api():
    """Handle chat sessions - GET to retrieve, POST to create."""
    try:
        # Get current user's registered profile
        if not current_user.registered_profile:
            return jsonify({"error": "User profile not found"}), 404
        
        registered_user_id = current_user.registered_profile.registered_user_id
        
        if request.method == 'POST':
            # Create a new session
            data = request.json or {}
            title = data.get('title', f"Chat session {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                new_session = ChatSession(registered_user_id=registered_user_id, title=title)
                db.session.add(new_session)
                db.session.commit()
                
                return jsonify({
                    "session_id": new_session.session_id,
                    "title": new_session.title,
                    "created_at": new_session.created_at.isoformat(),
                    "last_active": new_session.last_active.isoformat(),
                    "is_active": new_session.is_active
                })
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Failed to create ChatSession: {str(e)}")
                return jsonify({"error": "Failed to create chat session. Please try again."}), 500
        
        else:
            # GET: Return all sessions for the current user
            sessions = ChatSession.query.filter_by(registered_user_id=registered_user_id)\
                .order_by(ChatSession.last_active.desc()).all()
            
            result = [{
                "session_id": session.session_id,
                "title": session.title,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
                "is_active": session.is_active
            } for session in sessions]
            
            return jsonify({"sessions": result})
        
    except Exception as e:
        current_app.logger.error(f"Chat Sessions API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API endpoint for feedback
@chatbot_bp.route('/api/feedback', methods=['POST'])
@login_required
def feedback_api():
    """Record user feedback on answers."""
    data = request.json
    feedback = data.get('feedback')  # Simple thumbs up/down: 1 or -1
    chat_id = data.get('chat_id')
    
    # Detailed feedback metrics (optional)
    relevance = data.get('relevance')  # 1-5 scale
    accuracy = data.get('accuracy')    # 1-5 scale
    completeness = data.get('completeness')  # 1-5 scale 
    overall = data.get('overall')      # 1-5 scale
    feedback_text = data.get('feedback_text')  # Optional text feedback
    
    if feedback is None and relevance is None and overall is None and feedback_text is None:
        return jsonify({"error": "Missing feedback"}), 400
    
    try:
        # Find the most recent chat log for this user if chat_id not provided
        if chat_id is None:
            chat_log = ChatLog.query.filter_by(user_id=current_user.user_id)\
                .order_by(ChatLog.timestamp.desc()).first()
        else:
            chat_log = ChatLog.query.get(chat_id)
        
        if chat_log and chat_log.user_id == current_user.user_id:
            # Update simple feedback if provided
            if feedback is not None:
                chat_log.thumbs_up_down = feedback
            
            # Create detailed feedback record if any detailed metrics provided
            if relevance is not None or accuracy is not None or \
               completeness is not None or overall is not None or feedback_text:
                
                detailed_feedback = FeedbackDetail(
                    chat_log_id=chat_log.log_id,
                    user_id=current_user.user_id,
                    relevance_rating=relevance,
                    accuracy_rating=accuracy,
                    completeness_rating=completeness,
                    overall_rating=overall,
                    feedback_text=feedback_text
                )
                
                db.session.add(detailed_feedback)
            
            db.session.commit()
            return jsonify({"success": True})
        else:
            return jsonify({"error": "Chat log not found"}), 404
    
    except Exception as e:
        current_app.logger.error(f"Feedback API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API endpoint for chat history
@chatbot_bp.route('/api/chat/history', methods=['GET'])
@login_required
def get_chat_history():
    """Get chat history for a specific session."""
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
        
    try:
        # Get current user's registered profile
        if not current_user.registered_profile:
            return jsonify({"error": "User profile not found"}), 404
        
        registered_user_id = current_user.registered_profile.registered_user_id
        
        # Verify session belongs to current user
        session = ChatSession.query.filter_by(
            session_id=session_id,
            registered_user_id=registered_user_id
        ).first()
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
            
        # Get chat logs for this session
        chat_logs = ChatLog.query.filter_by(
            session_id=session_id
        ).order_by(ChatLog.timestamp.asc()).all()
        
        # Convert chat logs to conversational message pairs for frontend compatibility
        messages = []
        for chat in chat_logs:
            # Handle different AI response formats (JSON or plain text)
            try:
                # Try to parse as JSON first
                if chat.ai_response and chat.ai_response.startswith('{'): 
                    resp_data = json.loads(chat.ai_response)
                    answer_text = resp_data.get('answer', chat.ai_response)
                    citations = resp_data.get('citations', '')
                    extras = resp_data.get('extras', '')
                else:
                    answer_text = chat.ai_response
                    citations = ''
                    extras = ''
            except Exception:
                # Fall back to using raw response
                answer_text = chat.ai_response or 'No response available'
                citations = ''
                extras = ''
                
            # Create user message
            user_message = {
                "id": f"{chat.log_id}_user",
                "type": "user",
                "content": chat.user_prompt,
                "prompt": chat.user_prompt,
                "timestamp": chat.timestamp.isoformat(),
                "session_id": chat.session_id
            }
            messages.append(user_message)
            
            # Create AI message
            ai_message = {
                "id": f"{chat.log_id}_ai",
                "type": "ai",
                "content": answer_text,
                "answer": answer_text,
                "response": answer_text,
                "citations": citations,
                "extras": extras,
                "timestamp": chat.timestamp.isoformat(),
                "session_id": chat.session_id,
                "chat_id": chat.log_id,
                "log_id": chat.log_id,
                "feedback": "positive" if chat.thumbs_up_down == 1 else "negative" if chat.thumbs_up_down == -1 else None
            }
            messages.append(ai_message)
        
        return jsonify({"messages": messages, "chats": messages})
        
    except Exception as e:
        current_app.logger.error(f"Chat History API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API endpoint for retrieving individual chat
@chatbot_bp.route('/api/chat/<int:chat_id>', methods=['GET'])
@login_required
def get_chat_details(chat_id):
    """Get details of a specific chat interaction."""
    try:
        # Get chat log and verify ownership
        chat_log = ChatLog.query.filter_by(
            log_id=chat_id,
            user_id=current_user.user_id
        ).first()
        
        if not chat_log:
            return jsonify({"error": "Chat not found"}), 404
            
        # Parse saved AI response if available
        response_data = {}
        if chat_log.ai_response:
            try:
                response_data = json.loads(chat_log.ai_response)
            except:
                response_data = {"answer": "Error parsing saved response"}
        
        result = {
            "log_id": chat_log.log_id,
            "session_id": chat_log.session_id,
            "user_prompt": chat_log.user_prompt,
            "timestamp": chat_log.timestamp.isoformat(),
            "feedback": chat_log.thumbs_up_down,
            "answer": response_data.get('answer', ''),
            "citations": response_data.get('citations', ''),
            "extras": response_data.get('extras', '')
        }
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Chat Details API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API endpoint for detailed feedback
@chatbot_bp.route('/api/chat/feedback', methods=['POST'])
@login_required
def detailed_feedback_api():
    """Submit detailed feedback for a chat interaction."""
    data = request.json
    chat_id = data.get('chat_id')
    relevance = data.get('relevance')  # 1-5 scale
    accuracy = data.get('accuracy')    # 1-5 scale
    completeness = data.get('completeness')  # 1-5 scale
    overall = data.get('overall')      # 1-5 scale
    feedback_text = data.get('feedback_text')
    
    if not chat_id:
        return jsonify({"error": "Chat ID is required"}), 400
        
    try:
        # Verify chat log exists and belongs to current user
        chat_log = ChatLog.query.get(chat_id)
        if not chat_log or chat_log.user_id != current_user.user_id:
            return jsonify({"error": "Chat log not found"}), 404
            
        # Create new detailed feedback entry
        feedback = FeedbackDetail(
            chat_log_id=chat_id,
            user_id=current_user.user_id,
            relevance_rating=relevance,
            accuracy_rating=accuracy,
            completeness_rating=completeness,
            overall_rating=overall,
            feedback_text=feedback_text
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({"success": True, "feedback_id": feedback.feedback_id})
        
    except Exception as e:
        current_app.logger.error(f"Detailed Feedback API error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Admin role check decorator
def admin_required(f):
    """Decorator to check if the current user has admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(current_user, 'is_admin', False):
            return jsonify({"error": "Unauthorized"}), 403
        return f(*args, **kwargs)
    return decorated_function

# Admin metrics dashboard
@chatbot_bp.route('/admin/metrics')
@login_required
@admin_required
def admin_metrics():
    """Show admin metrics dashboard."""
    
    # Get metrics from database
    try:
        chat_logs = ChatLog.query.order_by(ChatLog.timestamp.desc()).limit(100).all()
        total_logs = ChatLog.query.count()
        
        # Calculate average latency
        avg_latency = db.session.query(db.func.avg(ChatLog.latency_ms)).scalar() or 0
        
        # Calculate satisfaction rate
        positive_feedback = ChatLog.query.filter(ChatLog.thumbs_up_down > 0).count()
        total_feedback = ChatLog.query.filter(ChatLog.thumbs_up_down != None).count()
        satisfaction_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0
        
        # Calculate average hit rate
        avg_hit_rate = db.session.query(db.func.avg(ChatLog.hit_rate)).scalar() or 0
        
        return render_template(
            'chatbot/admin_metrics.html',
            chat_logs=chat_logs,
            total_logs=total_logs,
            avg_latency=avg_latency,
            satisfaction_rate=satisfaction_rate,
            avg_hit_rate=avg_hit_rate,
            active_tab='metrics'
        )
    
    except Exception as e:
        current_app.logger.error(f"Admin metrics error: {str(e)}")
        flash(f"Error loading metrics: {str(e)}", 'danger')
        return render_template('chatbot/admin_metrics.html', active_tab='metrics')


# Admin metrics JSON API for Grafana
@chatbot_bp.route('/admin/metrics/json')
@login_required
@admin_required
def admin_metrics_json():
    """Provide metrics in JSON format for Grafana integration."""
    
    try:
        # Timeframe calculation
        now = datetime.utcnow()
        today = datetime(now.year, now.month, now.day)
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Base metrics
        total_logs = ChatLog.query.count()
        avg_latency = db.session.query(db.func.avg(ChatLog.latency_ms)).scalar() or 0
        avg_token_in = db.session.query(db.func.avg(ChatLog.token_in)).scalar() or 0
        avg_token_out = db.session.query(db.func.avg(ChatLog.token_out)).scalar() or 0
        avg_hit_rate = db.session.query(db.func.avg(ChatLog.hit_rate)).scalar() or 0
        
        # User satisfaction metrics
        positive_feedback = ChatLog.query.filter(ChatLog.thumbs_up_down > 0).count()
        negative_feedback = ChatLog.query.filter(ChatLog.thumbs_up_down < 0).count()
        total_feedback = positive_feedback + negative_feedback
        satisfaction_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0
        
        # Time-based metrics
        daily_logs = ChatLog.query.filter(ChatLog.timestamp >= yesterday).count()
        weekly_logs = ChatLog.query.filter(ChatLog.timestamp >= week_ago).count()
        monthly_logs = ChatLog.query.filter(ChatLog.timestamp >= month_ago).count()
        
        # Calculate average latency by time period
        daily_latency = db.session.query(db.func.avg(ChatLog.latency_ms)).filter(
            ChatLog.timestamp >= yesterday
        ).scalar() or 0
        
        weekly_latency = db.session.query(db.func.avg(ChatLog.latency_ms)).filter(
            ChatLog.timestamp >= week_ago
        ).scalar() or 0
        
        monthly_latency = db.session.query(db.func.avg(ChatLog.latency_ms)).filter(
            ChatLog.timestamp >= month_ago
        ).scalar() or 0
        
        # Hit rate over time
        daily_hit_rate = db.session.query(db.func.avg(ChatLog.hit_rate)).filter(
            ChatLog.timestamp >= yesterday
        ).scalar() or 0
        
        weekly_hit_rate = db.session.query(db.func.avg(ChatLog.hit_rate)).filter(
            ChatLog.timestamp >= week_ago
        ).scalar() or 0
        
        monthly_hit_rate = db.session.query(db.func.avg(ChatLog.hit_rate)).filter(
            ChatLog.timestamp >= month_ago
        ).scalar() or 0
        
        # Token usage metrics
        total_tokens_in = db.session.query(db.func.sum(ChatLog.token_in)).scalar() or 0
        total_tokens_out = db.session.query(db.func.sum(ChatLog.token_out)).scalar() or 0
        
        # Hourly usage pattern for the last 24 hours
        hourly_data = []
        for hour_offset in range(24):
            hour_start = now - timedelta(hours=hour_offset+1)
            hour_end = now - timedelta(hours=hour_offset)
            
            hour_count = ChatLog.query.filter(
                ChatLog.timestamp >= hour_start,
                ChatLog.timestamp < hour_end
            ).count()
            
            hourly_data.append({
                'hour': (now - timedelta(hours=hour_offset)).strftime('%H:00'),
                'count': hour_count
            })
        
        # Return structured JSON for Grafana
        return jsonify({
            'timestamp': now.isoformat(),
            'summary': {
                'total_logs': total_logs,
                'avg_latency_ms': round(avg_latency, 2),
                'avg_token_in': round(avg_token_in, 2),
                'avg_token_out': round(avg_token_out, 2),
                'avg_hit_rate': round(avg_hit_rate * 100, 2),  # Convert to percentage
                'satisfaction_rate': round(satisfaction_rate, 2),
                'total_tokens_processed': total_tokens_in + total_tokens_out
            },
            'time_based': {
                'daily': {
                    'logs': daily_logs,
                    'avg_latency_ms': round(daily_latency, 2),
                    'avg_hit_rate': round(daily_hit_rate * 100, 2)  # Convert to percentage
                },
                'weekly': {
                    'logs': weekly_logs,
                    'avg_latency_ms': round(weekly_latency, 2),
                    'avg_hit_rate': round(weekly_hit_rate * 100, 2)  # Convert to percentage
                },
                'monthly': {
                    'logs': monthly_logs,
                    'avg_latency_ms': round(monthly_latency, 2),
                    'avg_hit_rate': round(monthly_hit_rate * 100, 2)  # Convert to percentage
                }
            },
            'feedback': {
                'positive': positive_feedback,
                'negative': negative_feedback,
                'satisfaction_rate': round(satisfaction_rate, 2)
            },
            'hourly_usage': hourly_data,
            'version': '1.0.0'
        })
    
    except Exception as e:
        current_app.logger.error(f"Admin metrics JSON API error: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

# Paper indexing endpoint
@chatbot_bp.route('/admin/index-paper', methods=['POST'])
@login_required
@admin_required
def index_paper():
    """Index a paper from the ResHub database."""
    
    data = request.json
    paper_id = data.get('paper_id')
    
    if not paper_id:
        return jsonify({"error": "Missing paper_id"}), 400
    
    try:
        # Get paper from database
        from app.models import ResearchPaper
        paper = ResearchPaper.query.get(paper_id)
        
        if not paper:
            return jsonify({"error": "Paper not found"}), 404
        
        # Get file path
        file_path = os.path.join(current_app.root_path, 'static', 'uploads', 'papers', paper.file_path)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Paper file not found"}), 404
        
        # Prepare metadata
        metadata = {
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.publish_date.year if paper.publish_date else None,
            "source": "reshub",
            "source_id": str(paper.id),
            "url": url_for('paper.detail', paper_id=paper.id, _external=True)
        }
        
        # Process PDF
        document_id, stored_path, chunks = pdf_processor.process_pdf(file_path, metadata)
        
        # Add chunks to vector store
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}-{i}"
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["chunk_count"] = len(chunks)
            
            vector_store.add(chunk, chunk_metadata, chunk_id)
        
        return jsonify({
            "success": True,
            "document_id": document_id,
            "chunk_count": len(chunks)
        })
        
    except Exception as e:
        current_app.logger.error(f"Paper indexing error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Vector database admin dashboard
@chatbot_bp.route('/admin/vectors')
@login_required
@admin_required
def admin_vectors():
    """Show admin dashboard for vector database management."""
    try:
        # Get indexed documents from database
        documents = IndexedDocument.query.order_by(IndexedDocument.created_at.desc()).limit(100).all()
        
        # Calculate statistics
        doc_count = IndexedDocument.query.count()
        vector_count = db.session.query(db.func.sum(IndexedDocument.chunk_count)).scalar() or 0
        
        # Calculate storage used (estimate based on PDF file sizes)
        storage_used = 0
        pdf_store_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'pdf_store')
        if os.path.exists(pdf_store_dir):
            for file in os.listdir(pdf_store_dir):
                if file.endswith('.pdf'):
                    file_path = os.path.join(pdf_store_dir, file)
                    storage_used += os.path.getsize(file_path)
        
        # Format storage used
        if storage_used < 1024:
            storage_used_str = f"{storage_used} bytes"
        elif storage_used < 1024 * 1024:
            storage_used_str = f"{storage_used / 1024:.2f} KB"
        else:
            storage_used_str = f"{storage_used / (1024 * 1024):.2f} MB"
        
        # Get last indexed date
        last_doc = IndexedDocument.query.order_by(IndexedDocument.created_at.desc()).first()
        last_indexed = last_doc.created_at.strftime('%Y-%m-%d %H:%M:%S') if last_doc else "Never"
        
        return render_template(
            'chatbot/admin_vectors.html',
            documents=documents,
            doc_count=doc_count,
            vector_count=vector_count,
            storage_used=storage_used_str,
            last_indexed=last_indexed,
            active_tab='vectors'
        )
    
    except Exception as e:
        current_app.logger.error(f"Vector admin error: {str(e)}")
        flash(f"Error loading vector database info: {str(e)}", 'danger')
        return render_template('chatbot/admin_vectors.html', active_tab='vectors')

# Re-index all documents
@chatbot_bp.route('/admin/vectors/reindex', methods=['POST'])
@login_required
@admin_required
def reindex_all():
    """Re-index all documents in the database."""
    try:
        # Get all indexed documents
        documents = IndexedDocument.query.all()
        count = 0
        
        for doc in documents:
            # Get the file path
            file_path = doc.file_path
            
            if os.path.exists(file_path):
                # Prepare metadata
                metadata = {
                    "title": doc.title,
                    "authors": doc.authors,
                    "year": doc.year,
                    "source": doc.source,
                    "source_id": doc.source_id,
                    "url": doc.url
                }
                
                # Delete existing vectors from the database
                vector_store.client.delete(collection_name=vector_store.collection_name, 
                                           points_selector=f"metadata.document_id=={doc.document_id}")
                
                # Re-process PDF
                document_id, stored_path, chunks = pdf_processor.process_pdf(file_path, metadata)
                
                # Update indexed document record
                doc.chunk_count = len(chunks)
                doc.updated_at = datetime.utcnow()
                db.session.commit()
                
                # Add chunks to vector store
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{document_id}-{i}"
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = i
                    chunk_metadata["chunk_count"] = len(chunks)
                    chunk_metadata["document_id"] = document_id
                    
                    vector_store.add(chunk, chunk_metadata, chunk_id)
                
                count += 1
        
        return jsonify({
            "success": True,
            "count": count
        })
        
    except Exception as e:
        current_app.logger.error(f"Re-indexing error: {str(e)}")
        return jsonify({"error": str(e), "success": False})

# Purge orphan PDFs
@chatbot_bp.route('/admin/vectors/purge-orphans', methods=['POST'])
@login_required
@admin_required
def purge_orphans():
    """Delete PDF files that are not referenced in the database."""
    try:
        # Get all indexed document file paths
        indexed_paths = [doc.file_path for doc in IndexedDocument.query.all()]
        
        # Check all files in the PDF store directory
        pdf_store_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'pdf_store')
        count = 0
        space_freed = 0
        
        if os.path.exists(pdf_store_dir):
            for file in os.listdir(pdf_store_dir):
                if file.endswith('.pdf'):
                    file_path = os.path.join(pdf_store_dir, file)
                    
                    # Check if this file is not in the indexed documents
                    if file_path not in indexed_paths:
                        # Get file size before deleting
                        file_size = os.path.getsize(file_path)
                        space_freed += file_size
                        
                        # Delete the file
                        os.remove(file_path)
                        count += 1
        
        # Format space freed
        if space_freed < 1024:
            space_freed_str = f"{space_freed} bytes"
        elif space_freed < 1024 * 1024:
            space_freed_str = f"{space_freed / 1024:.2f} KB"
        else:
            space_freed_str = f"{space_freed / (1024 * 1024):.2f} MB"
        
        return jsonify({
            "success": True,
            "count": count,
            "space_freed": space_freed_str
        })
        
    except Exception as e:
        current_app.logger.error(f"Purge orphans error: {str(e)}")
        return jsonify({"error": str(e), "success": False})

# Download vectors CSV
@chatbot_bp.route('/admin/vectors/download-csv')
@login_required
@admin_required
def download_vectors_csv():
    """Download metadata of all indexed documents as CSV."""
    try:
        # Get all indexed documents
        documents = IndexedDocument.query.all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Document ID', 'Title', 'Authors', 'Year', 'Source', 'Source ID', 'URL', 'Chunks', 'Created At', 'Updated At'])
        
        # Write data rows
        for doc in documents:
            writer.writerow([
                doc.document_id,
                doc.title,
                doc.authors,
                doc.year,
                doc.source,
                doc.source_id,
                doc.url,
                doc.chunk_count,
                doc.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                doc.updated_at.strftime('%Y-%m-%d %H:%M:%S') if doc.updated_at else ''
            ])
        
        # Prepare response
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename=reshub_vectors_{timestamp}.csv"}
        )
        
    except Exception as e:
        current_app.logger.error(f"CSV download error: {str(e)}")
        flash(f"Error generating CSV: {str(e)}", 'danger')
        return redirect(url_for('chatbot.admin_vectors'))

# Delete document
@chatbot_bp.route('/admin/vectors/delete-document', methods=['POST'])
@login_required
@admin_required
def delete_document():
    """Delete a document and its vectors from the database."""
    try:
        data = request.json
        document_id = data.get('document_id')
        
        if not document_id:
            return jsonify({"error": "Missing document_id"}), 400
        
        # Find the document in the database
        document = IndexedDocument.query.filter_by(document_id=document_id).first()
        
        if not document:
            return jsonify({"error": "Document not found"}), 404
        
        # Delete the document file if it exists
        if document.file_path and os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete vectors from the vector store
        try:
            vector_store.client.delete(collection_name=vector_store.collection_name, 
                                      points_selector=f"metadata.document_id=={document_id}")
        except Exception as e:
            current_app.logger.warning(f"Could not delete vectors: {str(e)}")
        
        # Delete the document record from the database
        db.session.delete(document)
        db.session.commit()
        
        return jsonify({"success": True})
        
    except Exception as e:
        current_app.logger.error(f"Delete document error: {str(e)}")
        return jsonify({"error": str(e), "success": False})

# External API Search interface
@chatbot_bp.route('/admin/papers/search')
@login_required
@admin_required
def external_paper_search():
    """Interface for searching papers from external APIs."""
    return render_template('chatbot/paper_search.html')

# Search with CORE API
@chatbot_bp.route('/api/papers/search/core', methods=['GET'])
@login_required
@admin_required
def search_core_papers():
    """
    Search for papers in the CORE API.
    
    Query Parameters:
        query (str): The search query
        max_results (int, optional): Maximum number of results to return
        year (int, optional): Filter by publication year
    """
    from app.chatbot.error_handlers import handle_core_api_error, handle_missing_api_key, handle_bad_request
    
    query = request.args.get('query', '')
    max_results = request.args.get('max_results', 20, type=int)
    year_filter = request.args.get('year', None, type=int)
    
    if not query.strip():
        return handle_bad_request('Search query cannot be empty')
    
    # Get CORE API key from configuration
    core_api_key = current_app.config.get('CORE_API_KEY')
    if not core_api_key:
        return handle_missing_api_key('CORE')
    
    try:
        # Initialize CoreFetcher with the API key
        fetcher = CoreFetcher(core_api_key)
        
        # Search for papers
        try:
            results = fetcher.search(query, max_results=max_results, year_filter=year_filter)
        except requests.exceptions.HTTPError as http_err:
            # Specifically handle rate limit errors (HTTP 429)
            if http_err.response.status_code == 429:
                current_app.logger.warning(f"CORE API rate limit exceeded: {str(http_err)}")
                error_info = {
                    'error': str(http_err),
                    'code': 'rate_limit_exceeded',
                    'message': ERROR_CODES['rate_limit_exceeded']
                }
                
                # Include rate limit headers if available
                if 'X-Rate-Limit-Remaining' in http_err.response.headers:
                    error_info['rate_limit_remaining'] = http_err.response.headers['X-Rate-Limit-Remaining']
                if 'X-Rate-Limit-Reset' in http_err.response.headers:
                    error_info['rate_limit_reset'] = http_err.response.headers['X-Rate-Limit-Reset']
                
                return jsonify(error_info), 429
            else:
                # Handle other HTTP errors
                return handle_core_api_error(http_err)
        
        # Log rate limit information if available in CoreFetcher response headers
        if hasattr(fetcher, 'last_response_headers') and fetcher.last_response_headers:
            rate_limit_remaining = fetcher.last_response_headers.get('X-Rate-Limit-Remaining')
            if rate_limit_remaining is not None:
                current_app.logger.info(f"CORE API rate limit remaining: {rate_limit_remaining}")
        
        return jsonify({
            'source': 'core',
            'query': query,
            'results': results
        })
    
    except Exception as e:
        return handle_core_api_error(e)

# Import paper from CORE
@chatbot_bp.route('/api/papers/import/core', methods=['POST'])
@login_required
@admin_required
def import_core_paper():
    """Import a paper from CORE API into the vector database."""
    from app.chatbot.error_handlers import handle_core_api_error, handle_missing_api_key, handle_bad_request
    
    if not request.is_json:
        return handle_bad_request('Request must be JSON')
    
    paper_id = request.json.get('paper_id', None)
    if not paper_id:
        return handle_bad_request('paper_id is required')
    
    # Get CORE API key from configuration
    core_api_key = current_app.config.get('CORE_API_KEY')
    if not core_api_key:
        return handle_missing_api_key('CORE')
    
    fetcher = CoreFetcher(api_key=core_api_key)
    
    # Set PDF storage directory from config
    pdf_dir = current_app.config.get('PDF_STORAGE_PATH', 'app/static/uploads/pdf_store')
    
    try:
        # Check if we already have this paper in our database
        existing_paper = IndexedDocument.query.filter_by(source='core', source_id=paper_id).first()
        if existing_paper:
            return jsonify({
                "success": False, 
                "message": "Paper already exists in the database",
                "document_id": existing_paper.document_id,
                "code": "resource_exists"
            }), 409
        
        # First, search for the paper to get metadata
        paper_details = None
        
        try:
            search_results = fetcher.search(f"id:{paper_id}", max_results=1)
            
            # Log rate limit information
            if hasattr(fetcher, 'last_response_headers') and fetcher.last_response_headers:
                rate_limit_remaining = fetcher.last_response_headers.get('X-Rate-Limit-Remaining')
                if rate_limit_remaining is not None:
                    current_app.logger.info(f"CORE API rate limit remaining after search: {rate_limit_remaining}")
        except requests.exceptions.HTTPError as http_err:
            # Specifically handle rate limit errors (HTTP 429)
            if http_err.response.status_code == 429:
                current_app.logger.warning(f"CORE API rate limit exceeded during search: {str(http_err)}")
                error_info = {
                    'error': str(http_err),
                    'code': 'rate_limit_exceeded',
                    'message': ERROR_CODES['rate_limit_exceeded']
                }
                
                # Include rate limit headers if available
                if 'X-Rate-Limit-Remaining' in http_err.response.headers:
                    error_info['rate_limit_remaining'] = http_err.response.headers['X-Rate-Limit-Remaining']
                if 'X-Rate-Limit-Reset' in http_err.response.headers:
                    error_info['rate_limit_reset'] = http_err.response.headers['X-Rate-Limit-Reset']
                
                return jsonify(error_info), 429
            else:
                # Handle other HTTP errors
                return handle_core_api_error(http_err)
        
        if search_results and len(search_results) > 0:
            paper_details = search_results[0]
        
        if not paper_details:
            error_info = {
                "error": f"Paper with ID {paper_id} not found",
                "code": "resource_not_found"
            }
            current_app.logger.warning(f"CORE API paper not found: {paper_id}")
            return jsonify(error_info), 404
        
        # Download the paper PDF
        try:
            pdf_path, pdf_hash = fetcher.download_paper(paper_id, store_dir=pdf_dir)
            
            # Log rate limit information after download
            if hasattr(fetcher, 'last_response_headers') and fetcher.last_response_headers:
                rate_limit_remaining = fetcher.last_response_headers.get('X-Rate-Limit-Remaining')
                if rate_limit_remaining is not None:
                    current_app.logger.info(f"CORE API rate limit remaining after download: {rate_limit_remaining}")
        except requests.exceptions.HTTPError as http_err:
            # Specifically handle rate limit errors (HTTP 429)
            if http_err.response.status_code == 429:
                current_app.logger.warning(f"CORE API rate limit exceeded during download: {str(http_err)}")
                error_info = {
                    'error': str(http_err),
                    'code': 'rate_limit_exceeded',
                    'message': ERROR_CODES['rate_limit_exceeded']
                }
                
                # Include rate limit headers if available
                if 'X-Rate-Limit-Remaining' in http_err.response.headers:
                    error_info['rate_limit_remaining'] = http_err.response.headers['X-Rate-Limit-Remaining']
                if 'X-Rate-Limit-Reset' in http_err.response.headers:
                    error_info['rate_limit_reset'] = http_err.response.headers['X-Rate-Limit-Reset']
                
                return jsonify(error_info), 429
            else:
                # Handle other HTTP errors
                return handle_core_api_error(http_err)
        
        if not pdf_path or not pdf_hash:
            error_info = {
                "error": "Failed to download paper PDF",
                "code": "file_error"
            }
            current_app.logger.error(f"Failed to download CORE paper PDF: {paper_id}")
            return jsonify(error_info), 500
        
        # Extract text chunks from the PDF
        chunks = pdf_processor.extract_chunks(pdf_path)
        
        if not chunks or len(chunks) == 0:
            error_info = {
                "error": "Failed to extract text from PDF",
                "code": "data_processing_error"
            }
            current_app.logger.error(f"Failed to extract text from PDF: {pdf_path}")
            return jsonify(error_info), 500
        
        # Create a new document record
        document = IndexedDocument(
            document_id=pdf_hash,
            title=paper_details['title'],
            source='core',
            source_id=paper_id,
            authors=', '.join(paper_details.get('authors', [])),
            year=paper_details.get('year'),
            abstract=paper_details.get('abstract', ''),
            file_path=pdf_path,
            chunk_count=len(chunks),
            indexed_at=datetime.utcnow()
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Add chunks to vector store with paper metadata
        for i, chunk in enumerate(chunks):
            vector_store.add_chunk(
                chunk_id=f"{pdf_hash}_{i}",
                text=chunk,
                metadata={
                    'document_id': pdf_hash,
                    'title': paper_details['title'],
                    'authors': paper_details.get('authors', []),
                    'year': paper_details.get('year'),
                    'source': 'core',
                    'source_id': paper_id,
                    'chunk_number': i,
                    'total_chunks': len(chunks)
                }
            )
        
        current_app.logger.info(f"Successfully imported CORE paper: {paper_details['title']} ({paper_id})")
        return jsonify({
            "success": True,
            "message": "Paper imported successfully",
            "document_id": pdf_hash,
            "title": paper_details['title'],
            "chunks_indexed": len(chunks)
        })
    
    except Exception as e:
        return handle_core_api_error(e)
