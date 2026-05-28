import json
from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.adaptive import (
    estimate_proficiency_from_responses,
    select_next_question,
    select_session_question,
)
from app.admin import require_admin_session
from app.auth import create_session, get_student_from_token, hash_password, logout_token, verify_password
from app.coding import execute_python_code
from app.cognitive import classify_cognitive_state, generate_adaptive_explanation
from app.cognitive_summary import generate_cognitive_summary, serialize_cognitive_summary
from app.database import get_db
from app.llm_service import generate_questions_with_llm
from app.question_bank import (
    COURSES,
    ensure_sample_datasets,
    seed_questions_from_csv,
)
from app.simulator import (
    get_evaluation_summary,
    get_graph_results,
    run_research_simulation,
)


router = APIRouter()
ADAPTIVE_SESSION_QUESTION_LIMIT = 15


COURSE_DESCRIPTIONS = {
    "Python": "Programming foundations, functions, data structures, and problem solving.",
    "Machine Learning": "Supervised learning, metrics, features, and model reasoning.",
}


@router.get("/")
def root():
    """Health endpoint for confirming the API is running."""
    return {"message": "Adaptive Cognitive Learning System API running"}


@router.post(
    "/students",
    response_model=schemas.StudentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    """Create a learner profile or reject duplicate email addresses."""
    existing_student = (
        db.query(models.Student)
        .filter(models.Student.email == student.email)
        .first()
    )
    if existing_student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email already exists.",
        )

    db_student = models.Student(
        name=student.name,
        email=student.email,
        password_hash=hash_password(student.password) if student.password else None,
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student


@router.post("/auth/register", response_model=schemas.AuthRead, status_code=status.HTTP_201_CREATED)
def register(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    """Register and log in a student with lightweight session auth."""
    if not student.password:
        raise HTTPException(status_code=400, detail="Password is required.")
    created = create_student(student, db)
    return {"token": create_session(created.id), "student": created}


@router.post("/auth/login", response_model=schemas.AuthRead)
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Log in a student and return a simple bearer token."""
    student = db.query(models.Student).filter(models.Student.email == request.email).first()
    if not student or not verify_password(request.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"token": create_session(student.id), "student": student}


@router.post("/auth/logout")
def logout(authorization: str | None = Header(default=None)):
    """Log out by removing the server-side session token."""
    logout_token(_bearer_token(authorization))
    return {"message": "Logged out"}


@router.get("/auth/me", response_model=schemas.StudentRead)
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Return the currently logged-in student."""
    student = get_student_from_token(_bearer_token(authorization), db)
    if not student:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return student


@router.get("/courses", response_model=list[schemas.CourseRead])
def get_courses():
    """List available course tracks for the learning platform."""
    return [
        {"name": course, "description": COURSE_DESCRIPTIONS[course], "level": "Adaptive"}
        for course in COURSES
    ]


@router.get("/dashboard", response_model=schemas.DashboardRead)
def get_dashboard(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Get personalized dashboard for authenticated student."""
    student = get_student_from_token(_bearer_token(authorization), db)
    if not student:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    # Get enrolled courses
    enrollments = (
        db.query(models.CourseEnrollment)
        .filter(models.CourseEnrollment.student_id == student.id)
        .all()
    )
    enrollment_list = [
        schemas.CourseEnrollmentRead.model_validate(e) for e in enrollments
    ]
    enrolled_course_names = {e.course for e in enrollments}

    # Build course progress
    responses = _get_student_responses(student.id, db)
    course_progress = {}

    for course in COURSES:
        course_responses = [r for r in responses if r.question.course == course]
        course_progress[course] = schemas.DashboardCourseData(
            name=course,
            description=COURSE_DESCRIPTIONS[course],
            enrolled=course in enrolled_course_names,
            progress=len(course_responses) / 20 if course_responses else 0.0,
            question_count=len(course_responses),
        )

    # Overall proficiency
    proficiency = estimate_proficiency_from_responses(responses)

    return schemas.DashboardRead(
        student=schemas.StudentRead.model_validate(student),
        enrolled_courses=enrollment_list,
        course_progress=course_progress,
        proficiency_estimate=proficiency.estimate,
        uncertainty=proficiency.uncertainty,
    )


@router.post("/courses/{course_name}/enroll")
def enroll_in_course(
    course_name: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Enroll a student in a course."""
    student = get_student_from_token(_bearer_token(authorization), db)
    if not student:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    if course_name not in COURSES:
        raise HTTPException(status_code=400, detail="Invalid course name.")

    # Check if already enrolled
    existing = (
        db.query(models.CourseEnrollment)
        .filter(
            models.CourseEnrollment.student_id == student.id,
            models.CourseEnrollment.course == course_name,
        )
        .first()
    )
    if existing:
        return {"message": "Already enrolled in this course."}

    enrollment = models.CourseEnrollment(
        student_id=student.id,
        course=course_name,
    )
    db.add(enrollment)
    db.commit()

    return {"message": f"Successfully enrolled in {course_name}."}


@router.get("/courses/{course_name}")
def get_course_detail(
    course_name: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Get detailed course information."""
    student = get_student_from_token(_bearer_token(authorization), db)
    if not student:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    if course_name not in COURSES:
        raise HTTPException(status_code=400, detail="Invalid course name.")

    enrollment = (
        db.query(models.CourseEnrollment)
        .filter(
            models.CourseEnrollment.student_id == student.id,
            models.CourseEnrollment.course == course_name,
        )
        .first()
    )

    responses = _get_student_responses(student.id, db)
    course_responses = [r for r in responses if r.question.course == course_name]
    proficiency = estimate_proficiency_from_responses(course_responses)

    return {
        "name": course_name,
        "description": COURSE_DESCRIPTIONS.get(
            course_name, "Advanced adaptive learning course."
        ),
        "enrolled": enrollment is not None,
        "questions_answered": len(course_responses),
        "proficiency_estimate": proficiency.estimate,
        "uncertainty": proficiency.uncertainty,
        "topics": list(set(r.question.topic for r in course_responses if r.question.topic)),
    }


@router.post("/quiz/start/{course_name}")
def start_quiz_session(
    course_name: str,
    session_type: str = "mcq",
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Start a new quiz session for a course."""
    student = get_student_from_token(_bearer_token(authorization), db)
    if not student:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    if course_name not in COURSES:
        raise HTTPException(status_code=400, detail="Invalid course name.")

    # Create quiz session
    session = models.QuizSession(
        student_id=student.id,
        course=course_name,
        session_type=session_type,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    questions = _get_questions_for_course(db, course_name, session_type)
    student_responses = _get_student_responses(student.id, db)
    course_responses = _filter_responses_for_course(student_responses, course_name)
    proficiency = estimate_proficiency_from_responses(course_responses)

    next_question = select_session_question(
        questions=questions,
        proficiency_state=proficiency,
        session_responses=[],
        history_responses=course_responses,
    )

    return {
        "session_id": session.id,
        "course": course_name,
        "session_type": session_type,
        "next_question": _serialize_question(next_question) if next_question else None,
        "proficiency_estimate": proficiency.estimate,
        "question_limit": ADAPTIVE_SESSION_QUESTION_LIMIT,
        "question_count": 0,
        "session_complete": next_question is None,
    }


@router.post("/quiz/{session_id}/respond")
def submit_quiz_response(
    session_id: int,
    response: schemas.ResponseCreate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Submit a response during a quiz session."""
    student = get_student_from_token(_bearer_token(authorization), db)
    if not student:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    session = (
        db.query(models.QuizSession)
        .filter(models.QuizSession.id == session_id)
        .first()
    )
    if not session or session.student_id != student.id:
        raise HTTPException(status_code=404, detail="Quiz session not found.")
    if session.completed_at is not None:
        raise HTTPException(status_code=400, detail="This quiz session is already complete.")

    question = _get_question_or_404(response.question_id, db)
    if question.course != session.course or question.question_type != session.session_type:
        raise HTTPException(status_code=400, detail="Question does not belong to this quiz session.")
    if _question_already_used_in_session(session.id, question.id, db):
        raise HTTPException(status_code=400, detail="This question was already answered in the current session.")

    correctness = _is_answer_correct(response, question)

    db.add(
        models.Response(
            student_id=student.id,
            question_id=question.id,
            session_id=session.id,
            correctness=correctness,
            confidence_level=response.confidence_level,
            response_time=response.response_time,
            question_difficulty=question.difficulty,
            submitted_answer=response.submitted_answer,
        )
    )

    session.question_count += 1
    if correctness:
        session.correct_count += 1

    db.commit()
    db.refresh(session)

    student_responses = _get_student_responses(student.id, db)
    course_responses = _filter_responses_for_course(student_responses, session.course)
    session_responses = _get_session_responses(session.id, db)
    proficiency = estimate_proficiency_from_responses(course_responses)

    cognitive_state = classify_cognitive_state(
        correctness=correctness,
        confidence_level=response.confidence_level,
        response_time=response.response_time,
    )

    session_is_complete = session.question_count >= ADAPTIVE_SESSION_QUESTION_LIMIT
    next_question = None
    summary_payload = None

    if session_is_complete:
        summary_payload = _complete_quiz_session(session, student.id, session_responses, proficiency, db)
    else:
        questions = _get_questions_for_course(db, session.course, session.session_type)
        next_question = select_session_question(
            questions=questions,
            proficiency_state=proficiency,
            session_responses=session_responses,
            history_responses=course_responses,
            cognitive_state=cognitive_state,
        )
        session_is_complete = next_question is None
        if session_is_complete:
            summary_payload = _complete_quiz_session(session, student.id, session_responses, proficiency, db)

    explanation = generate_adaptive_explanation(
        cognitive_state,
        question.difficulty,
        next_question.difficulty if next_question else None,
    )

    result = {
        "session_id": session_id,
        "question_count": session.question_count,
        "question_limit": ADAPTIVE_SESSION_QUESTION_LIMIT,
        "correct_count": session.correct_count,
        "accuracy": session.correct_count / session.question_count,
        "proficiency_estimate": proficiency.estimate,
        "next_question": _serialize_question(next_question) if (next_question and not session_is_complete) else None,
        "cognitive_state": cognitive_state,
        "adaptive_explanation": explanation,
        "session_complete": session_is_complete,
        "converged": False,
    }
    if summary_payload:
        result["summary"] = summary_payload

    return result


@router.post("/quiz/{session_id}/finish")
def finish_quiz_session(
    session_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Finish a quiz session and generate cognitive summary."""
    student = get_student_from_token(_bearer_token(authorization), db)
    if not student:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    session = (
        db.query(models.QuizSession)
        .filter(models.QuizSession.id == session_id)
        .first()
    )
    if not session or session.student_id != student.id:
        raise HTTPException(status_code=404, detail="Quiz session not found.")
    if session.question_count < ADAPTIVE_SESSION_QUESTION_LIMIT and session.completed_at is None:
        raise HTTPException(
            status_code=400,
            detail=f"Adaptive sessions complete automatically after {ADAPTIVE_SESSION_QUESTION_LIMIT} questions.",
        )

    session_responses = _get_session_responses(session.id, db)
    proficiency = estimate_proficiency_from_responses(
        _filter_responses_for_course(_get_student_responses(student.id, db), session.course)
    )
    summary = _complete_quiz_session(session, student.id, session_responses, proficiency, db)

    return {
        "session_id": session.id,
        "status": "completed",
        "summary": summary,
    }


@router.get("/quiz/{session_id}/summary")
def get_quiz_summary(
    session_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Get the cognitive summary for a completed quiz session."""
    student = get_student_from_token(_bearer_token(authorization), db)
    if not student:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    session = (
        db.query(models.QuizSession)
        .filter(models.QuizSession.id == session_id)
        .first()
    )
    if not session or session.student_id != student.id:
        raise HTTPException(status_code=404, detail="Quiz session not found.")

    if not session.cognitive_summary:
        raise HTTPException(status_code=400, detail="Summary not yet generated.")

    return json.loads(session.cognitive_summary)


@router.get("/questions", response_model=list[schemas.QuestionRead])
def get_questions(
    course: str | None = None,
    question_type: str | None = None,
    db: Session = Depends(get_db),
):
    """Fetch questions for course pages, upload checks, or demos."""
    _ensure_question_bank(db)
    query = db.query(models.Question)
    if course:
        query = query.filter(models.Question.course == course)
    if question_type:
        query = query.filter(models.Question.question_type == question_type)
    return [_serialize_question(question) for question in query.limit(100).all()]


@router.post("/questions/generate-dataset")
def generate_dataset(db: Session = Depends(get_db)):
    """Create CSV datasets and seed SQLite with realistic sample questions."""
    dataset_info = ensure_sample_datasets()
    created = seed_questions_from_csv(db)
    return {**dataset_info, "seeded_questions": created}


@router.post("/questions/ai-generate")
def ai_generate_questions(request: schemas.LLMQuestionRequest):
    """Generate MCQs through the configured LLM provider or local mock mode."""
    return generate_questions_with_llm(
        course=request.course,
        topic=request.topic,
        difficulty=request.difficulty,
        count=request.count,
    )


@router.post(
    "/adaptive/start/{student_id}",
    response_model=schemas.AdaptiveAssessmentRead,
)
def start_adaptive_assessment(
    student_id: int,
    course: str = "Python",
    db: Session = Depends(get_db),
):
    """Start or resume a course-specific adaptive MCQ assessment."""
    student = _get_student_or_404(student_id, db)
    questions = _get_questions_for_course(db, course, "mcq")
    responses = _get_student_responses(student.id, db)

    proficiency = estimate_proficiency_from_responses(responses)
    available = _filter_unanswered_questions(questions, responses)
    next_question = _select_start_or_adaptive_question(available, proficiency, responses)

    return _assessment_payload(
        student.id,
        proficiency,
        next_question,
        None,
        "Adaptive assessment started with an easy course question.",
    )


@router.post(
    "/adaptive/respond",
    response_model=schemas.AdaptiveAssessmentRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_adaptive_response(
    response: schemas.ResponseCreate,
    db: Session = Depends(get_db),
):
    """Store an MCQ response, update proficiency, and return the next question."""
    student = _get_student_or_404(response.student_id, db)
    question = _get_question_or_404(response.question_id, db)
    correctness = _is_answer_correct(response, question)

    db.add(
        models.Response(
            student_id=student.id,
            question_id=question.id,
            correctness=correctness,
            confidence_level=response.confidence_level,
            response_time=response.response_time,
            question_difficulty=question.difficulty,
            submitted_answer=response.submitted_answer,
        )
    )
    db.commit()

    responses = _get_student_responses(student.id, db)
    proficiency = estimate_proficiency_from_responses(responses)
    questions = _get_questions_for_course(db, question.course, "mcq")
    next_question = select_next_question(_filter_unanswered_questions(questions, responses), proficiency)
    cognitive_state = classify_cognitive_state(
        correctness=correctness,
        confidence_level=response.confidence_level,
        response_time=response.response_time,
    )
    explanation = generate_adaptive_explanation(
        cognitive_state,
        question.difficulty,
        next_question.difficulty if next_question else None,
    )

    return _assessment_payload(student.id, proficiency, next_question, cognitive_state, explanation)


@router.post(
    "/coding/start/{student_id}",
    response_model=schemas.AdaptiveAssessmentRead,
)
def start_coding_assessment(
    student_id: int,
    course: str = "Python",
    db: Session = Depends(get_db),
):
    """Start adaptive coding practice for a selected course."""
    student = _get_student_or_404(student_id, db)
    responses = _get_student_responses(student.id, db)
    proficiency = estimate_proficiency_from_responses(responses)
    questions = _get_questions_for_course(db, course, "coding")
    next_question = _select_start_or_adaptive_question(questions, proficiency, responses)
    return _assessment_payload(
        student.id,
        proficiency,
        next_question,
        None,
        "Coding practice started. Submit code to adapt the next challenge.",
    )


@router.post("/coding/run")
def run_code(request: schemas.CodeExecutionRequest, db: Session = Depends(get_db)):
    """Run Python code safely enough for small educational examples."""
    question = None
    if request.question_id:
        question = _get_question_or_404(request.question_id, db)
    return execute_python_code(request.code, question.test_code if question else "")


@router.post(
    "/coding/respond",
    response_model=schemas.CodingAssessmentRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_coding_response(
    request: schemas.CodeExecutionRequest,
    db: Session = Depends(get_db),
):
    """Execute code, store result, and adapt coding difficulty."""
    if request.student_id is None or request.question_id is None:
        raise HTTPException(status_code=400, detail="student_id and question_id are required.")

    student = _get_student_or_404(request.student_id, db)
    question = _get_question_or_404(request.question_id, db)
    execution = execute_python_code(request.code, question.test_code or "")
    correctness = execution["success"]
    response_time = max(float(execution["execution_time"]), 1.0)
    confidence = 0.85 if correctness else 0.35

    db.add(
        models.Response(
            student_id=student.id,
            question_id=question.id,
            correctness=correctness,
            confidence_level=confidence,
            response_time=response_time,
            question_difficulty=question.difficulty,
            submitted_answer=request.code,
        )
    )
    db.commit()

    responses = _get_student_responses(student.id, db)
    proficiency = estimate_proficiency_from_responses(responses)
    questions = _get_questions_for_course(db, question.course, "coding")
    next_question = select_next_question(_filter_unanswered_questions(questions, responses), proficiency)
    cognitive_state = classify_cognitive_state(correctness, confidence, response_time)
    explanation = generate_adaptive_explanation(
        cognitive_state,
        question.difficulty,
        next_question.difficulty if next_question else None,
    )

    return {
        **_assessment_payload(student.id, proficiency, next_question, cognitive_state, explanation),
        "execution": execution,
    }


@router.get("/progress/{student_id}")
def get_progress(student_id: int, db: Session = Depends(get_db)):
    """Return personalized progress data across courses."""
    _get_student_or_404(student_id, db)
    responses = _get_student_responses(student_id, db)
    proficiency = estimate_proficiency_from_responses(responses)
    course_counts = {}
    for response in responses:
        course = response.question.course if response.question else "Unknown"
        course_counts[course] = course_counts.get(course, 0) + 1

    return {
        "student_id": student_id,
        "proficiency_estimate": proficiency.estimate,
        "uncertainty": proficiency.uncertainty,
        "answered": len(responses),
        "course_counts": course_counts,
    }


@router.post("/simulation/run")
def run_simulation(username: str = Depends(require_admin_session)):
    """Run a seminar-friendly random-vs-adaptive evaluation simulation."""
    return run_research_simulation()


@router.get("/simulation/graphs")
def fetch_simulation_graphs(username: str = Depends(require_admin_session)):
    """Fetch paths to the latest generated evaluation graphs."""
    return get_graph_results()


@router.get("/simulation/summary")
def fetch_simulation_summary(username: str = Depends(require_admin_session)):
    """Fetch the latest random-vs-adaptive evaluation summary."""
    return get_evaluation_summary()


# ============================================================================
# INTERNAL RESEARCH ENDPOINTS - Hidden from learners, for paper/conference use
# ============================================================================


@router.post("/internal/evaluation/run")
def internal_run_simulation(username: str = Depends(require_admin_session)):
    """[INTERNAL] Run research simulation for paper evaluation."""
    return run_research_simulation()


@router.get("/internal/evaluation/graphs")
def internal_fetch_simulation_graphs(username: str = Depends(require_admin_session)):
    """[INTERNAL] Fetch evaluation graphs for research presentations."""
    return get_graph_results()


@router.get("/internal/evaluation/summary")
def internal_fetch_simulation_summary(username: str = Depends(require_admin_session)):
    """[INTERNAL] Fetch evaluation summary for research analysis."""
    return get_evaluation_summary()


@router.get("/internal/students", response_model=list[schemas.StudentRead])
def internal_get_students(
    username: str = Depends(require_admin_session),
    db: Session = Depends(get_db),
):
    """[INTERNAL] Fetch all registered students for research analysis."""
    return db.query(models.Student).all()


def _ensure_question_bank(db: Session):
    ensure_sample_datasets()
    if db.query(models.Question).count() < 20:
        seed_questions_from_csv(db)


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    return authorization


def _get_student_or_404(student_id: int, db: Session) -> models.Student:
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student


def _get_question_or_404(question_id: int, db: Session) -> models.Question:
    question = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")
    return question


def _get_student_responses(student_id: int, db: Session) -> list[models.Response]:
    return (
        db.query(models.Response)
        .filter(models.Response.student_id == student_id)
        .order_by(models.Response.id)
        .all()
    )


def _get_session_responses(session_id: int, db: Session) -> list[models.Response]:
    return (
        db.query(models.Response)
        .filter(models.Response.session_id == session_id)
        .order_by(models.Response.id)
        .all()
    )


def _filter_responses_for_course(
    responses: list[models.Response],
    course: str,
) -> list[models.Response]:
    return [
        response
        for response in responses
        if response.question and response.question.course == course
    ]


def _question_already_used_in_session(
    session_id: int,
    question_id: int,
    db: Session,
) -> bool:
    return (
        db.query(models.Response)
        .filter(models.Response.session_id == session_id)
        .filter(models.Response.question_id == question_id)
        .first()
        is not None
    )


def _get_questions_for_course(db: Session, course: str, question_type: str) -> list[models.Question]:
    _ensure_question_bank(db)
    query = (
        db.query(models.Question)
        .filter(models.Question.course == course)
        .filter(models.Question.question_type == question_type)
    )
    if question_type == "mcq":
        query = query.filter(models.Question.options.isnot(None))
    if question_type == "coding":
        query = query.filter(models.Question.starter_code.isnot(None))
    return query.order_by(models.Question.difficulty).all()


def _filter_unanswered_questions(
    questions: list[models.Question],
    responses: list[models.Response],
) -> list[models.Question]:
    answered_ids = {response.question_id for response in responses}
    available = [question for question in questions if question.id not in answered_ids]
    return available or questions


def _select_start_or_adaptive_question(questions, proficiency, responses):
    if not responses:
        easy_questions = [question for question in questions if question.difficulty <= 0.35]
        return easy_questions[0] if easy_questions else (questions[0] if questions else None)
    return select_next_question(questions, proficiency)


def _is_answer_correct(response: schemas.ResponseCreate, question: models.Question) -> bool:
    if response.correctness is not None:
        return response.correctness
    return (response.submitted_answer or "").strip().upper() == (question.correct_answer or "").strip().upper()


def _complete_quiz_session(
    session: models.QuizSession,
    student_id: int,
    session_responses: list[models.Response],
    proficiency,
    db: Session,
) -> dict:
    session.completed_at = session.completed_at or datetime.utcnow()
    session.proficiency_estimate = proficiency.estimate

    summary = generate_cognitive_summary(
        session_id=session.id,
        student_id=student_id,
        course=session.course,
        session_responses=session_responses,
        proficiency_estimate=proficiency.estimate,
    )
    serialized_summary = serialize_cognitive_summary(summary)
    session.cognitive_summary = json.dumps(serialized_summary)
    db.commit()
    return serialized_summary


def _assessment_payload(student_id, proficiency, next_question, cognitive_state, explanation):
    return {
        "student_id": student_id,
        "proficiency_estimate": proficiency.estimate,
        "uncertainty": proficiency.uncertainty,
        "next_question": _serialize_question(next_question) if next_question else None,
        "cognitive_state": cognitive_state,
        "adaptive_explanation": explanation,
    }


def _serialize_question(question: models.Question | None):
    if not question:
        return None
    options = None
    if question.options:
        try:
            options = json.loads(question.options)
        except json.JSONDecodeError:
            options = [question.options]
    return {
        "id": question.id,
        "course": question.course,
        "text": question.text,
        "topic": question.topic,
        "difficulty": question.difficulty,
        "difficulty_label": question.difficulty_label,
        "question_type": question.question_type,
        "options": options,
        "explanation": question.explanation,
        "starter_code": question.starter_code,
    }
