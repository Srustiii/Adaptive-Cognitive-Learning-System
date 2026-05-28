"""Generate adaptive cognitive summaries after quiz sessions."""

import json
from typing import Any

from app.cognitive import classify_cognitive_state
from app.models import Response
from app.schemas import CognitiveSummary


def generate_cognitive_summary(
    session_id: int,
    student_id: int,
    course: str,
    session_responses: list[Response],
    proficiency_estimate: float,
) -> CognitiveSummary:
    """Generate an intelligent learner feedback summary from a quiz session.

    Analyzes:
    - correctness patterns
    - confidence levels
    - response times
    - hesitation behavior
    - misconception detection
    - topic-specific performance

    Returns personalized recommendations for learning focus areas.
    """
    if not session_responses:
        return CognitiveSummary(
            session_id=session_id,
            student_id=student_id,
            course=course,
            questions_answered=0,
            correct_count=0,
            accuracy=0.0,
            proficiency_estimate=proficiency_estimate,
            strongest_topics=[],
            weakest_topics=[],
            hesitation_areas=[],
            misconceptions_detected=[],
            recommendations=["Begin the course with foundational concepts."],
            cognitive_patterns={},
        )

    # Calculate basic metrics
    correct_count = sum(1 for r in session_responses if r.correctness)
    accuracy = correct_count / len(session_responses)

    # Analyze by topic
    topic_performance = {}
    topic_hesitation = {}
    topic_confidence = {}

    for response in session_responses:
        topic = response.question.topic or "general"

        if topic not in topic_performance:
            topic_performance[topic] = {"correct": 0, "total": 0}
            topic_hesitation[topic] = []
            topic_confidence[topic] = []

        topic_performance[topic]["total"] += 1
        if response.correctness:
            topic_performance[topic]["correct"] += 1

        topic_confidence[topic].append(response.confidence_level)
        topic_hesitation[topic].append(response.response_time)

    # Classify cognitive states and detect patterns
    cognitive_states = []
    misconceptions = []
    confusion_areas = []
    hesitation_areas = []

    for response in session_responses:
        state = classify_cognitive_state(
            response.correctness,
            response.confidence_level,
            response.response_time,
        )
        cognitive_states.append(state)

        if state == "misconception":
            topic = response.question.topic or "general"
            misconceptions.append(topic)

        if state == "confusion":
            topic = response.question.topic or "general"
            confusion_areas.append(topic)

        # Hesitation: slow response + low confidence
        if (
            response.response_time > 40
            and response.confidence_level < 0.4
        ):
            topic = response.question.topic or "general"
            hesitation_areas.append(topic)

    # Identify strongest and weakest topics
    strongest_topics = []
    weakest_topics = []

    for topic, perf in topic_performance.items():
        if perf["total"] >= 2:
            topic_accuracy = perf["correct"] / perf["total"]
            if topic_accuracy >= 0.8:
                strongest_topics.append(topic)
            elif topic_accuracy < 0.5:
                weakest_topics.append(topic)

    # Remove duplicates and limit to top 3
    strongest_topics = list(dict.fromkeys(strongest_topics))[:3]
    weakest_topics = list(dict.fromkeys(weakest_topics))[:3]
    misconceptions = list(dict.fromkeys(misconceptions))[:3]
    hesitation_areas = list(dict.fromkeys(hesitation_areas))[:3]

    # Generate recommendations
    recommendations = _generate_recommendations(
        accuracy,
        proficiency_estimate,
        strongest_topics,
        weakest_topics,
        misconceptions,
        hesitation_areas,
    )

    # Build cognitive patterns
    cognitive_patterns = {
        "mastery_count": sum(1 for s in cognitive_states if s == "mastery"),
        "confusion_count": sum(1 for s in cognitive_states if s == "confusion"),
        "misconception_count": sum(
            1 for s in cognitive_states if s == "misconception"
        ),
        "partial_understanding_count": sum(
            1 for s in cognitive_states if s == "partial_understanding"
        ),
        "confidence_trend": _calculate_confidence_trend(session_responses),
        "speed_trend": _calculate_speed_trend(session_responses),
    }

    return CognitiveSummary(
        session_id=session_id,
        student_id=student_id,
        course=course,
        questions_answered=len(session_responses),
        correct_count=correct_count,
        accuracy=accuracy,
        proficiency_estimate=proficiency_estimate,
        strongest_topics=strongest_topics,
        weakest_topics=weakest_topics,
        hesitation_areas=hesitation_areas,
        misconceptions_detected=misconceptions,
        recommendations=recommendations,
        cognitive_patterns=cognitive_patterns,
    )


def _generate_recommendations(
    accuracy: float,
    proficiency: float,
    strongest: list[str],
    weakest: list[str],
    misconceptions: list[str],
    hesitation: list[str],
) -> list[str]:
    """Generate learning recommendations based on performance analysis."""
    recommendations = []

    # Performance-based recommendations
    if accuracy >= 0.8:
        recommendations.append(
            "Excellent performance! You've demonstrated strong understanding. "
            "Consider challenging yourself with harder problems."
        )
    elif accuracy >= 0.6:
        recommendations.append(
            "Good progress! Continue practicing to solidify your understanding. "
            "Focus on areas where you struggled."
        )
    else:
        recommendations.append(
            "You're just getting started. Revisit foundational concepts and practice regularly."
        )

    # Topic-specific recommendations
    if strongest:
        strongest_str = ", ".join(strongest[:2])
        recommendations.append(
            f"Strong understanding of {strongest_str} detected. Build on this foundation."
        )

    if weakest:
        weakest_str = ", ".join(weakest[:2])
        recommendations.append(
            f"Focus your next session on {weakest_str} to improve proficiency."
        )

    if misconceptions:
        misconceptions_str = ", ".join(misconceptions[:2])
        recommendations.append(
            f"Possible misconceptions detected in {misconceptions_str}. "
            "Review the explanations carefully."
        )

    if hesitation:
        hesitation_str = ", ".join(hesitation[:2])
        recommendations.append(
            f"You showed hesitation in {hesitation_str}. "
            "Take time to understand the core concepts before moving on."
        )

    if proficiency < 0.4:
        recommendations.append(
            "The system will adapt to show you more foundational questions next time."
        )
    elif proficiency > 0.7:
        recommendations.append(
            "Ready for challenge? The next session will include harder problems."
        )

    return recommendations[:5]  # Limit to top 5 recommendations


def _calculate_confidence_trend(responses: list[Response]) -> str:
    """Analyze confidence trend across session."""
    if len(responses) < 2:
        return "insufficient_data"

    first_half_confidence = [
        r.confidence_level for r in responses[: len(responses) // 2]
    ]
    second_half_confidence = [
        r.confidence_level for r in responses[len(responses) // 2 :]
    ]

    first_avg = sum(first_half_confidence) / len(first_half_confidence)
    second_avg = sum(second_half_confidence) / len(second_half_confidence)

    if second_avg > first_avg + 0.1:
        return "increasing"
    elif second_avg < first_avg - 0.1:
        return "decreasing"
    else:
        return "stable"


def _calculate_speed_trend(responses: list[Response]) -> str:
    """Analyze response speed trend across session."""
    if len(responses) < 2:
        return "insufficient_data"

    first_half_times = [
        r.response_time for r in responses[: len(responses) // 2]
    ]
    second_half_times = [
        r.response_time for r in responses[len(responses) // 2 :]
    ]

    first_avg = sum(first_half_times) / len(first_half_times)
    second_avg = sum(second_half_times) / len(second_half_times)

    if second_avg < first_avg - 5:  # At least 5 seconds faster
        return "improving"
    elif second_avg > first_avg + 5:  # At least 5 seconds slower
        return "slowing"
    else:
        return "consistent"


def serialize_cognitive_summary(summary: CognitiveSummary) -> dict[str, Any]:
    """Serialize a CognitiveSummary to JSON-friendly dict."""
    return {
        "session_id": summary.session_id,
        "student_id": summary.student_id,
        "course": summary.course,
        "questions_answered": summary.questions_answered,
        "correct_count": summary.correct_count,
        "accuracy": round(summary.accuracy, 2),
        "proficiency_estimate": round(summary.proficiency_estimate, 2),
        "strongest_topics": summary.strongest_topics,
        "weakest_topics": summary.weakest_topics,
        "hesitation_areas": summary.hesitation_areas,
        "misconceptions_detected": summary.misconceptions_detected,
        "recommendations": summary.recommendations,
        "cognitive_patterns": summary.cognitive_patterns,
    }
