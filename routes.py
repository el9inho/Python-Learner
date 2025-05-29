import json
import uuid
from flask import render_template, request, jsonify, session
from app import app, db
from models import LessonProgress, CodeExecution
from code_runner import execute_python_code

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
    
    # Get progress for this session
    progress = LessonProgress.query.filter_by(session_id=session['session_id']).all()
    completed_lessons = [p.lesson_id for p in progress if p.completed]
    
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
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
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
    
    # Save progress
    progress = LessonProgress.query.filter_by(
        session_id=session['session_id'],
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = LessonProgress(
            session_id=session['session_id'],
            lesson_id=lesson_id
        )
        db.session.add(progress)
    
    progress.quiz_score = score
    progress.completed = score >= 70  # Pass threshold
    db.session.commit()
    
    return jsonify({
        'score': score,
        'passed': score >= 70,
        'results': results
    })

@app.route('/practice')
def practice():
    return render_template('practice.html')

@app.route('/run_code', methods=['POST'])
def run_code():
    data = request.get_json()
    code = data.get('code', '')
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Execute the code safely
    result = execute_python_code(code)
    
    # Save execution record
    execution = CodeExecution(
        session_id=session['session_id'],
        code=code,
        output=result.get('output', ''),
        error=result.get('error', '')
    )
    db.session.add(execution)
    db.session.commit()
    
    return jsonify(result)

@app.route('/complete_lesson', methods=['POST'])
def complete_lesson():
    data = request.get_json()
    lesson_id = data.get('lesson_id')
    
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Mark lesson as completed
    progress = LessonProgress.query.filter_by(
        session_id=session['session_id'],
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = LessonProgress(
            session_id=session['session_id'],
            lesson_id=lesson_id
        )
        db.session.add(progress)
    
    progress.completed = True
    db.session.commit()
    
    return jsonify({'success': True})
