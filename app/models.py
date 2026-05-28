from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Student(Base):
    """Stores learner identity information for adaptive learning research."""

    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    responses = relationship("Response", back_populates="student")
    enrollments = relationship("CourseEnrollment", back_populates="student")
    quiz_sessions = relationship("QuizSession", back_populates="student")


class Question(Base):
    """Represents an MCQ or coding question for a course."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    course = Column(String, index=True, nullable=False, default="Python")
    text = Column(String, nullable=False)
    topic = Column(String, nullable=True)
    difficulty = Column(Float, nullable=False, default=0.5)
    difficulty_label = Column(String, nullable=False, default="easy")
    question_type = Column(String, nullable=False, default="mcq")
    options = Column(Text, nullable=True)
    correct_answer = Column(String, nullable=True)
    explanation = Column(Text, nullable=True)
    starter_code = Column(Text, nullable=True)
    test_code = Column(Text, nullable=True)

    responses = relationship("Response", back_populates="question")


class Response(Base):
    """Tracks correctness, confidence, response time, and difficulty for analysis."""

    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"), nullable=True)
    correctness = Column(Boolean, nullable=False)
    confidence_level = Column(Float, nullable=False)
    response_time = Column(Float, nullable=False)
    question_difficulty = Column(Float, nullable=False)
    submitted_answer = Column(Text, nullable=True)

    student = relationship("Student", back_populates="responses")
    question = relationship("Question", back_populates="responses")
    quiz_session = relationship("QuizSession", back_populates="responses")


class CourseEnrollment(Base):
    """Tracks which courses a student is enrolled in and progress."""

    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course = Column(String, nullable=False)
    enrolled_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, nullable=True)

    student = relationship("Student", back_populates="enrollments")


class QuizSession(Base):
    """Represents a quiz/assessment session with configurable limits and tracking."""

    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course = Column(String, nullable=False)
    session_type = Column(String, nullable=False, default="mcq")  # 'mcq' or 'coding'
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    question_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    proficiency_estimate = Column(Float, nullable=True)
    cognitive_summary = Column(Text, nullable=True)  # JSON-serialized summary

    student = relationship("Student", back_populates="quiz_sessions")
    responses = relationship("Response", back_populates="quiz_session")
