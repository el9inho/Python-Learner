from flask import jsonify, session
from app import app, db
from models import User, LessonProgress, CodeExecution, QuizAttempt, LearningAnalytics
from datetime import datetime, timezone
from sqlalchemy import func, desc

@app.route('/api/user_stats')
def user_stats():
    """Get comprehensive user statistics and progress"""
    if 'session_id' not in session:
        return jsonify({'error': 'No session found'}), 404
    
    session_id = session['session_id']
    
    # Get user stats
    user = User.query.filter_by(session_id=session_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Lesson progress stats
    total_lessons = 3  # Based on lessons.json
    completed_lessons = LessonProgress.query.filter_by(
        session_id=session_id, 
        completed=True
    ).count()
    
    # Quiz stats
    quiz_attempts = QuizAttempt.query.filter_by(session_id=session_id).all()
    total_quiz_attempts = len(quiz_attempts)
    passed_quizzes = len([q for q in quiz_attempts if q.passed])
    
    # Calculate average score
    avg_score = 0
    if quiz_attempts:
        avg_score = sum(q.score for q in quiz_attempts) / len(quiz_attempts)
    
    # Code execution stats
    code_executions = CodeExecution.query.filter_by(session_id=session_id).all()
    total_code_runs = len(code_executions)
    successful_runs = len([c for c in code_executions if c.success])
    
    # Calculate success rate
    success_rate = 0
    if total_code_runs > 0:
        success_rate = (successful_runs / total_code_runs) * 100
    
    # Learning streak (days with activity)
    recent_activity = LearningAnalytics.query.filter_by(
        session_id=session_id
    ).order_by(desc(LearningAnalytics.timestamp)).limit(7).all()
    
    return jsonify({
        'user_id': session_id,
        'created_at': user.created_at.isoformat(),
        'last_active': user.last_active.isoformat(),
        'progress': {
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons,
            'completion_percentage': (completed_lessons / total_lessons) * 100
        },
        'quiz_performance': {
            'total_attempts': total_quiz_attempts,
            'passed_quizzes': passed_quizzes,
            'average_score': round(avg_score, 1),
            'pass_rate': round((passed_quizzes / max(total_quiz_attempts, 1)) * 100, 1)
        },
        'coding_activity': {
            'total_executions': total_code_runs,
            'successful_executions': successful_runs,
            'success_rate': round(success_rate, 1)
        },
        'recent_activity_days': len(set(a.timestamp.date() for a in recent_activity))
    })

@app.route('/api/leaderboard')
def leaderboard():
    """Get anonymized leaderboard data"""
    
    # Get top performers by lesson completion
    top_completers = db.session.query(
        User.session_id,
        func.count(LessonProgress.id).label('completed_count'),
        func.max(User.last_active).label('last_active')
    ).join(LessonProgress, User.session_id == LessonProgress.session_id)\
     .filter(LessonProgress.completed == True)\
     .group_by(User.session_id)\
     .order_by(desc('completed_count'), desc('last_active'))\
     .limit(10).all()
    
    # Get top quiz performers
    top_quiz_performers = db.session.query(
        User.session_id,
        func.avg(QuizAttempt.score).label('avg_score'),
        func.count(QuizAttempt.id).label('quiz_count')
    ).join(QuizAttempt, User.session_id == QuizAttempt.session_id)\
     .group_by(User.session_id)\
     .having(func.count(QuizAttempt.id) >= 2)\
     .order_by(desc('avg_score'))\
     .limit(10).all()
    
    # Get most active coders
    top_coders = db.session.query(
        User.session_id,
        func.count(CodeExecution.id).label('execution_count'),
        func.avg(CodeExecution.success.cast(db.Integer)).label('success_rate')
    ).join(CodeExecution, User.session_id == CodeExecution.session_id)\
     .group_by(User.session_id)\
     .having(func.count(CodeExecution.id) >= 5)\
     .order_by(desc('execution_count'))\
     .limit(10).all()
    
    # Anonymize session IDs for privacy
    def anonymize_id(session_id):
        return f"User_{hash(session_id) % 10000:04d}"
    
    return jsonify({
        'lesson_completers': [
            {
                'user': anonymize_id(user.session_id),
                'completed_lessons': user.completed_count,
                'last_active': user.last_active.isoformat() if user.last_active else None
            }
            for user in top_completers
        ],
        'quiz_champions': [
            {
                'user': anonymize_id(user.session_id),
                'average_score': round(float(user.avg_score), 1),
                'quiz_attempts': user.quiz_count
            }
            for user in top_quiz_performers
        ],
        'coding_enthusiasts': [
            {
                'user': anonymize_id(user.session_id),
                'code_executions': user.execution_count,
                'success_rate': round(float(user.success_rate or 0) * 100, 1)
            }
            for user in top_coders
        ]
    })

@app.route('/api/achievements')
def achievements():
    """Get user achievements and badges"""
    if 'session_id' not in session:
        return jsonify({'error': 'No session found'}), 404
    
    session_id = session['session_id']
    
    # Get user data
    completed_lessons = LessonProgress.query.filter_by(
        session_id=session_id, completed=True
    ).count()
    
    quiz_attempts = QuizAttempt.query.filter_by(session_id=session_id).all()
    perfect_scores = len([q for q in quiz_attempts if q.score == 100])
    
    code_executions = CodeExecution.query.filter_by(session_id=session_id).all()
    successful_runs = len([c for c in code_executions if c.success])
    
    # Define achievements
    achievements = []
    
    # Lesson completion achievements
    if completed_lessons >= 1:
        achievements.append({
            'id': 'first_lesson',
            'title': 'First Steps',
            'description': 'Completed your first lesson',
            'icon': 'fa-baby',
            'earned': True
        })
    
    if completed_lessons >= 3:
        achievements.append({
            'id': 'lesson_master',
            'title': 'Lesson Master',
            'description': 'Completed all available lessons',
            'icon': 'fa-graduation-cap',
            'earned': True
        })
    
    # Quiz achievements
    if perfect_scores >= 1:
        achievements.append({
            'id': 'perfect_score',
            'title': 'Perfect Score',
            'description': 'Scored 100% on a quiz',
            'icon': 'fa-star',
            'earned': True
        })
    
    if len(quiz_attempts) >= 3:
        achievements.append({
            'id': 'quiz_taker',
            'title': 'Quiz Enthusiast',
            'description': 'Attempted 3 or more quizzes',
            'icon': 'fa-question-circle',
            'earned': True
        })
    
    # Coding achievements
    if successful_runs >= 10:
        achievements.append({
            'id': 'code_runner',
            'title': 'Code Runner',
            'description': 'Successfully executed 10 code snippets',
            'icon': 'fa-code',
            'earned': True
        })
    
    if successful_runs >= 50:
        achievements.append({
            'id': 'coding_ninja',
            'title': 'Coding Ninja',
            'description': 'Successfully executed 50 code snippets',
            'icon': 'fa-user-ninja',
            'earned': True
        })
    
    # Calculate completion percentage
    total_possible = 6  # Total number of achievements
    earned_count = len(achievements)
    
    return jsonify({
        'achievements': achievements,
        'total_earned': earned_count,
        'total_possible': total_possible,
        'completion_percentage': round((earned_count / total_possible) * 100, 1)
    })