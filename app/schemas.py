from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentBase(BaseModel):
    name: str
    email: EmailStr


class StudentCreate(StudentBase):
    """Input schema for creating a student."""

    password: str | None = None


class StudentRead(StudentBase):
    """Output schema returned by student API endpoints."""

    id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthRead(BaseModel):
    token: str
    student: StudentRead


class QuestionRead(BaseModel):
    """Question data returned during adaptive assessment."""

    id: int
    course: str = "Python"
    text: str
    topic: str | None
    difficulty: float
    difficulty_label: str = "easy"
    question_type: str = "mcq"
    options: list[str] | None = None
    explanation: str | None = None
    starter_code: str | None = None


class AdaptiveAssessmentRead(BaseModel):
    """Adaptive state and next question returned to the client."""

    student_id: int
    proficiency_estimate: float
    uncertainty: float
    next_question: QuestionRead | None
    cognitive_state: str | None = None
    adaptive_explanation: str | None = None


class ResponseCreate(BaseModel):
    """Input schema for submitting an adaptive assessment response."""

    student_id: int
    question_id: int
    correctness: bool | None = None
    submitted_answer: str | None = None
    confidence_level: float = Field(ge=0.0, le=1.0)
    response_time: float = Field(gt=0.0)


class CourseRead(BaseModel):
    name: str
    description: str
    level: str


class LLMQuestionRequest(BaseModel):
    course: str
    topic: str
    difficulty: str = "easy"
    count: int = Field(default=3, ge=1, le=10)


class CodeExecutionRequest(BaseModel):
    student_id: int | None = None
    question_id: int | None = None
    code: str


class CodingAssessmentRead(BaseModel):
    student_id: int
    proficiency_estimate: float
    uncertainty: float
    next_question: QuestionRead | None
    execution: dict
    cognitive_state: str
    adaptive_explanation: str


class CourseEnrollmentRead(BaseModel):
    """Course enrollment information."""

    id: int
    course: str
    enrolled_at: datetime
    last_accessed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DashboardCourseData(BaseModel):
    """Course data for the dashboard."""

    name: str
    description: str
    enrolled: bool
    progress: float = 0.0
    question_count: int = 0


class DashboardRead(BaseModel):
    """Dashboard data for a student."""

    student: StudentRead
    enrolled_courses: list[CourseEnrollmentRead]
    course_progress: dict[str, DashboardCourseData]
    recent_activity: list[dict] | None = None
    proficiency_estimate: float = 0.5
    uncertainty: float = 1.0


class CognitiveSummary(BaseModel):
    """Adaptive cognitive summary after a quiz session."""

    session_id: int
    student_id: int
    course: str
    questions_answered: int
    correct_count: int
    accuracy: float
    proficiency_estimate: float
    strongest_topics: list[str]
    weakest_topics: list[str]
    hesitation_areas: list[str]
    misconceptions_detected: list[str]
    recommendations: list[str]
    cognitive_patterns: dict | None = None


class QuizSessionRead(BaseModel):
    """Quiz session information."""

    id: int
    course: str
    session_type: str
    started_at: datetime
    completed_at: datetime | None = None
    question_count: int
    correct_count: int
    proficiency_estimate: float | None = None
    cognitive_summary: dict | None = None

    model_config = ConfigDict(from_attributes=True)
