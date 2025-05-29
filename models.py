from app import db
from datetime import datetime, timezone
from sqlalchemy import Index

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    lesson_progress = db.relationship('LessonProgress', backref='user', lazy=True, cascade='all, delete-orphan')
    code_executions = db.relationship('CodeExecution', backref='user', lazy=True, cascade='all, delete-orphan')
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.session_id}>'

class LessonProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('user.session_id'), nullable=False)
    lesson_id = db.Column(db.String(64), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    time_spent_minutes = db.Column(db.Integer, default=0)
    
    # Create composite index for efficient queries
    __table_args__ = (
        Index('idx_session_lesson', 'session_id', 'lesson_id'),
    )
    
    def __repr__(self):
        return f'<LessonProgress {self.lesson_id} - {self.completed}>'

class CodeExecution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('user.session_id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    output = db.Column(db.Text)
    error = db.Column(db.Text)
    success = db.Column(db.Boolean, nullable=False)
    execution_time_ms = db.Column(db.Integer, default=0)
    executed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    lesson_id = db.Column(db.String(64), nullable=True)  # Optional: track which lesson the code was from
    
    def __repr__(self):
        return f'<CodeExecution {self.id} - {"Success" if self.success else "Error"}>'

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('user.session_id'), nullable=False)
    lesson_id = db.Column(db.String(64), nullable=False)
    quiz_id = db.Column(db.String(64), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    passed = db.Column(db.Boolean, nullable=False)
    answers = db.Column(db.JSON)  # Store user answers as JSON
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    time_taken_seconds = db.Column(db.Integer, default=0)
    
    # Create composite index for efficient queries
    __table_args__ = (
        Index('idx_session_quiz', 'session_id', 'lesson_id', 'quiz_id'),
    )
    
    def __repr__(self):
        return f'<QuizAttempt {self.lesson_id} - {self.score}/{self.max_score}>'

class LearningAnalytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), db.ForeignKey('user.session_id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # lesson_start, lesson_complete, code_run, quiz_attempt
    lesson_id = db.Column(db.String(64), nullable=True)
    data = db.Column(db.JSON)  # Additional event data
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<LearningAnalytics {self.event_type} - {self.lesson_id}>'
