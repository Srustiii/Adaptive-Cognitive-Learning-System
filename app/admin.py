import os
import secrets
from collections import Counter, defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import models
from app.adaptive import estimate_proficiency_from_responses
from app.database import get_db


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ADMIN_COOKIE_NAME = "adaptivelearn_admin_session"
ADMIN_SESSIONS: dict[str, str] = {}

router = APIRouter()


def require_admin_session(request: Request) -> str:
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if not token or token not in ADMIN_SESSIONS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin login required.")
    return ADMIN_SESSIONS[token]


def admin_page(request: Request, filename: str):
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if not token or token not in ADMIN_SESSIONS:
        return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    return FileResponse(STATIC_DIR / filename)


@router.get("/admin/login", include_in_schema=False)
def admin_login_page():
    return FileResponse(STATIC_DIR / "admin_login.html")


@router.get("/admin/dashboard", include_in_schema=False)
def admin_dashboard_page(request: Request):
    return admin_page(request, "admin_dashboard.html")


@router.get("/admin/research", include_in_schema=False)
def admin_research_page(request: Request):
    return admin_page(request, "admin_research.html")


@router.get("/admin/analytics", include_in_schema=False)
def admin_analytics_page(request: Request):
    return admin_page(request, "admin_analytics.html")


@router.post("/admin/api/login")
async def admin_login(request: Request, response: Response):
    credentials = await request.json()
    expected_username = os.getenv("ADMIN_USERNAME")
    expected_password = os.getenv("ADMIN_PASSWORD")

    if not expected_username or not expected_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin credentials are not configured.",
        )

    if (
        credentials.get("username") != expected_username
        or credentials.get("password") != expected_password
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials.")

    token = secrets.token_urlsafe(32)
    ADMIN_SESSIONS[token] = expected_username
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=os.getenv("RENDER") == "true",
        max_age=60 * 60 * 8,
    )
    return {"message": "Admin login successful.", "username": expected_username}


@router.post("/admin/api/logout")
def admin_logout(request: Request, response: Response):
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if token:
        ADMIN_SESSIONS.pop(token, None)
    response.delete_cookie(ADMIN_COOKIE_NAME)
    return {"message": "Admin logged out."}


@router.get("/admin/api/me")
def admin_me(username: str = Depends(require_admin_session)):
    return {"username": username}


@router.get("/admin/api/dashboard")
def admin_dashboard(
    username: str = Depends(require_admin_session),
    db: Session = Depends(get_db),
):
    responses = db.query(models.Response).order_by(models.Response.id).all()
    sessions = db.query(models.QuizSession).all()
    learner_count = db.query(models.Student).count()
    active_sessions = sum(1 for session in sessions if session.completed_at is None)
    proficiency = estimate_proficiency_from_responses(responses)

    misconception_count = sum(
        1 for response in responses if not response.correctness and response.confidence_level >= 0.75
    )
    hesitation_count = sum(
        1 for response in responses if response.response_time >= 30 or response.confidence_level <= 0.35
    )
    average_confidence = _average([response.confidence_level for response in responses])

    return {
        "learner_count": learner_count,
        "active_quiz_sessions": active_sessions,
        "average_proficiency": proficiency.estimate,
        "misconception_count": misconception_count,
        "hesitation_count": hesitation_count,
        "average_confidence": average_confidence,
        "confidence_trends": _confidence_trends(responses),
        "misconception_topics": _topic_counts(
            response for response in responses if not response.correctness and response.confidence_level >= 0.75
        ),
        "hesitation_topics": _topic_counts(
            response for response in responses if response.response_time >= 30 or response.confidence_level <= 0.35
        ),
    }


@router.get("/admin/api/analytics")
def admin_analytics(
    username: str = Depends(require_admin_session),
    db: Session = Depends(get_db),
):
    students = db.query(models.Student).order_by(models.Student.id).all()
    responses = db.query(models.Response).order_by(models.Response.id).all()
    responses_by_student = defaultdict(list)
    for response in responses:
        responses_by_student[response.student_id].append(response)

    learners = []
    for student in students:
        student_responses = responses_by_student.get(student.id, [])
        proficiency = estimate_proficiency_from_responses(student_responses)
        learners.append(
            {
                "id": student.id,
                "name": student.name,
                "email": student.email,
                "responses": len(student_responses),
                "proficiency": proficiency.estimate,
                "average_confidence": _average([r.confidence_level for r in student_responses]),
                "average_response_time": _average([r.response_time for r in student_responses]),
                "hesitation_count": sum(
                    1 for r in student_responses if r.response_time >= 30 or r.confidence_level <= 0.35
                ),
                "misconception_count": sum(
                    1 for r in student_responses if not r.correctness and r.confidence_level >= 0.75
                ),
            }
        )

    return {
        "learners": learners,
        "confidence_distribution": _confidence_distribution(responses),
        "difficulty_progression": _difficulty_progression(responses),
        "hesitation_frequency": _topic_counts(
            response for response in responses if response.response_time >= 30 or response.confidence_level <= 0.35
        ),
        "proficiency_tracking": [
            {"student": learner["name"], "proficiency": learner["proficiency"]}
            for learner in learners
        ],
    }


def _average(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _confidence_trends(responses: list[models.Response]) -> list[dict]:
    buckets = []
    bucket_size = 5
    for index in range(0, len(responses), bucket_size):
        bucket = responses[index : index + bucket_size]
        buckets.append(
            {
                "label": f"{index + 1}-{index + len(bucket)}",
                "average_confidence": _average(response.confidence_level for response in bucket),
            }
        )
    return buckets


def _topic_counts(responses) -> list[dict]:
    counter = Counter()
    for response in responses:
        topic = response.question.topic if response.question and response.question.topic else "Unknown"
        counter[topic] += 1
    return [{"topic": topic, "count": count} for topic, count in counter.most_common(8)]


def _confidence_distribution(responses: list[models.Response]) -> list[dict]:
    bins = {"low": 0, "medium": 0, "high": 0}
    for response in responses:
        if response.confidence_level < 0.4:
            bins["low"] += 1
        elif response.confidence_level < 0.75:
            bins["medium"] += 1
        else:
            bins["high"] += 1
    return [{"label": label, "count": count} for label, count in bins.items()]


def _difficulty_progression(responses: list[models.Response]) -> list[dict]:
    by_level = defaultdict(list)
    for response in responses:
        if response.question_difficulty <= 0.35:
            label = "easy"
        elif response.question_difficulty <= 0.7:
            label = "medium"
        else:
            label = "hard"
        by_level[label].append(response)

    return [
        {
            "label": label,
            "count": len(items),
            "accuracy": _average(1.0 if response.correctness else 0.0 for response in items),
        }
        for label, items in by_level.items()
    ]
