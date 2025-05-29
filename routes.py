import json
import uuid
import time
from datetime import datetime, timezone
from flask import render_template, request, jsonify, session
from app import app, db
from models import User, LessonProgress, CodeExecution, QuizAttempt, LearningAnalytics
from code_runner import execute_python_code

# Helper function to ensure user exists
def get_or_create_user(session_id):
    user = User.query.filter_by(session_id=session_id).first()
    if not user:
        user = User()
        user.session_id = session_id
        user.created_at = datetime.now(timezone.utc)
        user.last_active = datetime.now(timezone.utc)
        db.session.add(user)
        db.session.commit()
    else:
        # Update last active time
        user.last_active = datetime.now(timezone.utc)
        db.session.commit()
    return user

# Load lessons data
def load_lessons():
    try:
        with open('lessons/lessons.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"lessons": []}

@app.route('/')
def index():
    lessons_data = load_lessons()
    # Get session ID for progress tracking
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Ensure user exists in database
    user = get_or_create_user(session['session_id'])
    
    # Get progress for this session
    progress = LessonProgress.query.filter_by(session_id=session['session_id']).all()
    completed_lessons = [p.lesson_id for p in progress if p.completed]
    
    # Track page visit
    analytics = LearningAnalytics(
        session_id=session['session_id'],
        event_type='page_visit',
        data={'page': 'home'}
    )
    db.session.add(analytics)
    db.session.commit()
    
    return render_template('index.html', 
                         lessons=lessons_data['lessons'][:3],  # Show first 3 lessons on home
                         completed_lessons=completed_lessons)

@app.route('/lessons')
def lessons():
    lessons_data = load_lessons()
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Get progress for this session
    progress = LessonProgress.query.filter_by(session_id=session['session_id']).all()
    completed_lessons = [p.lesson_id for p in progress if p.completed]
    
    return render_template('lessons.html', 
                         lessons=lessons_data['lessons'],
                         completed_lessons=completed_lessons)

@app.route('/lesson/<lesson_id>')
def lesson(lesson_id):
    lessons_data = load_lessons()
    lesson_data = None
    
    for lesson in lessons_data['lessons']:
        if lesson['id'] == lesson_id:
            lesson_data = lesson
            break
    
    if not lesson_data:
        return "Lesson not found", 404
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('lesson.html', lesson=lesson_data)

@app.route('/quiz/<lesson_id>')
def quiz(lesson_id):
    lessons_data = load_lessons()
    lesson_data = None
    
    for lesson in lessons_data['lessons']:
        if lesson['id'] == lesson_id:
            lesson_data = lesson
            break
    
    if not lesson_data or 'quiz' not in lesson_data:
        return "Quiz not found", 404
    
    return render_template('quiz.html', lesson=lesson_data)

@app.route('/submit_quiz', methods=['POST'])
def submit_quiz():
    data = request.get_json()
    lesson_id = data.get('lesson_id')
    answers = data.get('answers', {})
    start_time = data.get('start_time', time.time())
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Ensure user exists
    user = get_or_create_user(session['session_id'])
    
    # Load lesson to check answers
    lessons_data = load_lessons()
    lesson_data = None
    
    for lesson in lessons_data['lessons']:
        if lesson['id'] == lesson_id:
            lesson_data = lesson
            break
    
    if not lesson_data:
        return jsonify({'error': 'Lesson not found'}), 404
    
    # Calculate score
    quiz = lesson_data.get('quiz', {})
    questions = quiz.get('questions', [])
    correct_count = 0
    results = []
    
    for i, question in enumerate(questions):
        question_id = str(i)
        user_answer = answers.get(question_id)
        correct_answer = question.get('correct')
        is_correct = user_answer == correct_answer
        
        if is_correct:
            correct_count += 1
        
        results.append({
            'question_id': question_id,
            'correct': is_correct,
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'explanation': question.get('explanation', '')
        })
    
    score = int((correct_count / len(questions)) * 100) if questions else 0
    time_taken = int(time.time() - start_time)
    passed = score >= 70
    
    # Save quiz attempt
    quiz_attempt = QuizAttempt(
        session_id=session['session_id'],
        lesson_id=lesson_id,
        quiz_id=quiz.get('title', 'quiz'),
        score=score,
        max_score=100,
        passed=passed,
        answers=answers,
        time_taken_seconds=time_taken
    )
    db.session.add(quiz_attempt)
    
    # Update or create lesson progress
    progress = LessonProgress.query.filter_by(
        session_id=session['session_id'],
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = LessonProgress(
            session_id=session['session_id'],
            lesson_id=lesson_id,
            completed=passed
        )
        db.session.add(progress)
    else:
        if passed and not progress.completed:
            progress.completed = True
            progress.completed_at = datetime.now(timezone.utc)
    
    # Track analytics
    analytics = LearningAnalytics(
        session_id=session['session_id'],
        event_type='quiz_attempt',
        lesson_id=lesson_id,
        data={
            'score': score,
            'passed': passed,
            'time_taken': time_taken,
            'attempt_number': QuizAttempt.query.filter_by(
                session_id=session['session_id'],
                lesson_id=lesson_id
            ).count() + 1
        }
    )
    db.session.add(analytics)
    
    db.session.commit()
    
    return jsonify({
        'score': score,
        'passed': passed,
        'results': results,
        'time_taken': time_taken
    })

@app.route('/practice')
def practice():
    return render_template('practice.html')

@app.route('/run_code', methods=['POST'])
def run_code():
    data = request.get_json()
    code = data.get('code', '')
    lesson_id = data.get('lesson_id', None)  # Optional: track which lesson
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Ensure user exists
    user = get_or_create_user(session['session_id'])
    
    # Execute the code safely
    start_time = time.time()
    result = execute_python_code(code)
    execution_time = int((time.time() - start_time) * 1000)  # milliseconds
    
    # Save execution record
    execution = CodeExecution()
    execution.session_id = session['session_id']
    execution.code = code
    execution.output = result.get('output', '')
    execution.error = result.get('error', '')
    execution.success = result.get('success', False)
    execution.execution_time_ms = execution_time
    execution.lesson_id = lesson_id
    
    db.session.add(execution)
    
    # Track analytics
    analytics = LearningAnalytics()
    analytics.session_id = session['session_id']
    analytics.event_type = 'code_execution'
    analytics.lesson_id = lesson_id
    analytics.data = {
        'success': result.get('success', False),
        'execution_time_ms': execution_time,
        'code_length': len(code),
        'has_error': bool(result.get('error'))
    }
    
    db.session.add(analytics)
    db.session.commit()
    
    return jsonify(result)

@app.route('/complete_lesson', methods=['POST'])
def complete_lesson():
    data = request.get_json()
    lesson_id = data.get('lesson_id')
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Ensure user exists
    user = get_or_create_user(session['session_id'])
    
    # Mark lesson as completed
    progress = LessonProgress.query.filter_by(
        session_id=session['session_id'],
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = LessonProgress()
        progress.session_id = session['session_id']
        progress.lesson_id = lesson_id
        progress.completed = True
        progress.completed_at = datetime.now(timezone.utc)
        db.session.add(progress)
    else:
        if not progress.completed:
            progress.completed = True
            progress.completed_at = datetime.now(timezone.utc)
    
    # Track analytics
    analytics = LearningAnalytics()
    analytics.session_id = session['session_id']
    analytics.event_type = 'lesson_complete'
    analytics.lesson_id = lesson_id
    analytics.data = {'manually_completed': True}
    
    db.session.add(analytics)
    db.session.commit()
    
    return jsonify({'success': True})
