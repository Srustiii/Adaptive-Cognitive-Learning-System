import random
from collections import Counter, defaultdict
from dataclasses import dataclass

from app.models import Question, Response

@dataclass
class ProficiencyState:
    """Simple Beta distribution state for a student's current proficiency."""

    alpha: float
    beta: float

    @property
    def estimate(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def uncertainty(self) -> float:
        return 1 / (self.alpha + self.beta)


def initialize_student_proficiency() -> ProficiencyState:
    """Start each student with a neutral Bayesian prior.

    Beta(1, 1) means the system initially assumes no strong evidence about
    proficiency. The mean is 0.5, so the first question is usually medium.
    """
    return ProficiencyState(alpha=1.0, beta=1.0)


def update_proficiency(
    current_state: ProficiencyState,
    correctness: bool,
    confidence_level: float,
    response_time: float,
    question_difficulty: float,
) -> ProficiencyState:
    """Update proficiency using correctness, confidence, speed, and difficulty.

    This is a lightweight Bayesian-style update. Correct answers add evidence
    to alpha, incorrect answers add evidence to beta. Confidence and response
    time adjust how strong that evidence is, while harder questions count more
    when answered correctly.
    """
    confidence = _clamp(confidence_level, 0.0, 1.0)
    difficulty = _clamp(question_difficulty, 0.0, 1.0)
    speed_score = _response_speed_score(response_time)

    evidence_weight = 0.5 + (0.3 * confidence) + (0.2 * speed_score)

    if correctness:
        difficulty_bonus = 0.5 + difficulty
        return ProficiencyState(
            alpha=current_state.alpha + (evidence_weight * difficulty_bonus),
            beta=current_state.beta,
        )

    difficulty_relief = 1.5 - difficulty
    return ProficiencyState(
        alpha=current_state.alpha,
        beta=current_state.beta + (evidence_weight * difficulty_relief),
    )


def estimate_proficiency_from_responses(responses: list[Response]) -> ProficiencyState:
    """Rebuild the current proficiency estimate from stored response history."""
    state = initialize_student_proficiency()
    for response in responses:
        state = update_proficiency(
            current_state=state,
            correctness=response.correctness,
            confidence_level=response.confidence_level,
            response_time=response.response_time,
            question_difficulty=response.question_difficulty,
        )
    return state


def select_next_question(
    questions: list[Question],
    proficiency_state: ProficiencyState,
) -> Question | None:
    """Select the next question using Thompson Sampling.

    Thompson Sampling balances exploration and exploitation by sampling a
    possible proficiency value from the student's Beta distribution. When the
    system is uncertain, samples vary more, so it naturally explores easier and
    harder questions. As evidence grows, samples concentrate near the estimated
    proficiency and the system exploits what it has learned.
    """
    if not questions:
        return None

    sampled_proficiency = random.betavariate(
        proficiency_state.alpha,
        proficiency_state.beta,
    )

    return min(
        questions,
        key=lambda question: abs(question.difficulty - sampled_proficiency),
    )


def select_session_question(
    questions: list[Question],
    proficiency_state: ProficiencyState,
    session_responses: list[Response],
    history_responses: list[Response],
    cognitive_state: str | None = None,
) -> Question | None:
    """Select a behavior-aware non-repeated question for a 15-question session.

    The selector still uses Thompson Sampling for adaptive exploration, then
    adjusts the score with lightweight explainable rules:
    - struggling learners get easier/remedial questions near weak topics
    - successful learners move gradually toward harder questions
    - session topics are balanced to avoid repetitive flows
    - a small random exploration term makes each session path different
    """
    used_question_ids = {response.question_id for response in session_responses}
    candidates = [question for question in questions if question.id not in used_question_ids]
    if not candidates:
        return None

    sampled_proficiency = random.betavariate(
        proficiency_state.alpha,
        proficiency_state.beta,
    )
    target_difficulty = _target_difficulty(
        sampled_proficiency=sampled_proficiency,
        session_responses=session_responses,
        cognitive_state=cognitive_state,
    )
    weak_topics = _weak_topics(history_responses)
    session_topic_counts = Counter(
        response.question.topic for response in session_responses if response.question and response.question.topic
    )
    last_topic = _last_topic(session_responses)

    def score(question: Question) -> float:
        topic = question.topic or "general"
        difficulty_score = abs(question.difficulty - target_difficulty)
        repetition_penalty = session_topic_counts[topic] * 0.16
        same_topic_penalty = 0.08 if last_topic == topic and cognitive_state not in {"confusion", "misconception"} else 0.0
        remediation_bonus = -0.18 if cognitive_state in {"confusion", "misconception"} and topic in weak_topics else 0.0
        coverage_bonus = -0.10 if session_topic_counts[topic] == 0 else 0.0
        exploration_noise = random.uniform(0.0, 0.08)
        return (
            difficulty_score
            + repetition_penalty
            + same_topic_penalty
            + remediation_bonus
            + coverage_bonus
            + exploration_noise
        )

    return min(candidates, key=score)


def select_next_question_difficulty(proficiency_state: ProficiencyState) -> float:
    """Return a sampled target difficulty for explaining adaptive behavior."""
    return random.betavariate(proficiency_state.alpha, proficiency_state.beta)


def _target_difficulty(
    sampled_proficiency: float,
    session_responses: list[Response],
    cognitive_state: str | None,
) -> float:
    if not session_responses:
        return random.uniform(0.20, 0.38)

    previous_difficulty = session_responses[-1].question_difficulty
    target = (sampled_proficiency * 0.65) + (previous_difficulty * 0.35)

    if cognitive_state == "mastery":
        target = max(target, previous_difficulty + 0.16)
    elif cognitive_state == "partial_understanding":
        target = max(0.25, target + 0.04)
    elif cognitive_state == "misconception":
        target = min(target, previous_difficulty - 0.12)
    elif cognitive_state == "confusion":
        target = min(target, previous_difficulty - 0.20)

    answered = len(session_responses)
    if answered >= 10:
        target += 0.08
    elif answered >= 5:
        target += 0.04

    return _clamp(target, 0.15, 0.90)


def _weak_topics(history_responses: list[Response]) -> set[str]:
    topic_totals = defaultdict(lambda: {"correct": 0, "total": 0})
    for response in history_responses:
        if not response.question or not response.question.topic:
            continue
        stats = topic_totals[response.question.topic]
        stats["total"] += 1
        if response.correctness:
            stats["correct"] += 1

    weak = set()
    for topic, stats in topic_totals.items():
        accuracy = stats["correct"] / stats["total"] if stats["total"] else 0
        if stats["total"] >= 2 and accuracy < 0.60:
            weak.add(topic)
    return weak


def _last_topic(session_responses: list[Response]) -> str | None:
    if not session_responses:
        return None
    question = session_responses[-1].question
    return question.topic if question else None


def _response_speed_score(response_time: float) -> float:
    """Map response time to a simple 0-1 speed score.

    Faster confident answers provide slightly stronger evidence. Very slow
    answers still count, but the update is gentler because hesitation may
    indicate uncertainty.
    """
    if response_time <= 10:
        return 1.0
    if response_time >= 60:
        return 0.0
    return (60 - response_time) / 50


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))
