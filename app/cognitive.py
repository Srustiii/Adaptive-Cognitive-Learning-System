FAST_RESPONSE_SECONDS = 15
SLOW_RESPONSE_SECONDS = 40
HIGH_CONFIDENCE = 0.7
LOW_CONFIDENCE = 0.4


def classify_cognitive_state(
    correctness: bool,
    confidence_level: float,
    response_time: float,
) -> str:
    """Classify cognitive state using correctness, confidence, and hesitation.

    The rules are intentionally simple for research explanation:
    correctness shows performance, confidence shows self-belief, and response
    time is used as a lightweight hesitation signal.
    """
    confidence = _clamp(confidence_level, 0.0, 1.0)
    is_fast = response_time <= FAST_RESPONSE_SECONDS
    is_slow = response_time >= SLOW_RESPONSE_SECONDS
    high_confidence = confidence >= HIGH_CONFIDENCE
    low_confidence = confidence <= LOW_CONFIDENCE

    if correctness and is_fast and high_confidence:
        return "mastery"

    if not correctness and is_fast and high_confidence:
        return "misconception"

    if not correctness and is_slow and low_confidence:
        return "confusion"

    if correctness:
        return "partial_understanding"

    if not correctness and low_confidence:
        return "confusion"

    return "misconception"


def generate_adaptive_explanation(
    cognitive_state: str,
    previous_difficulty: float,
    next_difficulty: float | None,
) -> str:
    """Explain why the adaptive engine selected the next difficulty.

    The explanation connects the rule-based cognitive diagnosis with the next
    question choice, making the adaptive behavior easier to discuss in a
    seminar or research report.
    """
    difficulty_trend = _difficulty_trend(previous_difficulty, next_difficulty)

    if cognitive_state == "mastery":
        if difficulty_trend == "increased":
            return "Difficulty increased because the student demonstrated mastery with high confidence."
        return "Mastery detected from a fast, correct, high-confidence response."

    if cognitive_state == "partial_understanding":
        if difficulty_trend == "reduced":
            return "Difficulty reduced due to hesitation and low confidence despite a correct answer."
        return "Partial understanding detected because the answer was correct but showed some uncertainty."

    if cognitive_state == "misconception":
        return "Possible misconception detected due to a high-confidence incorrect answer."

    if difficulty_trend == "reduced":
        return "Difficulty reduced due to hesitation and low confidence."

    return "Confusion detected due to an incorrect answer with hesitation or low confidence."


def _difficulty_trend(previous_difficulty: float, next_difficulty: float | None) -> str:
    if next_difficulty is None:
        return "unchanged"
    if next_difficulty > previous_difficulty + 0.05:
        return "increased"
    if next_difficulty < previous_difficulty - 0.05:
        return "reduced"
    return "unchanged"


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))
