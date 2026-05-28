import json
import os
import urllib.request


def generate_questions_with_llm(course: str, topic: str, difficulty: str, count: int) -> dict:
    """Generate questions through Gemini, OpenAI-compatible, or gateway APIs.

    Provider is selected with LLM_PROVIDER:
    - openai: OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
    - gemini: GEMINI_API_KEY, GEMINI_MODEL
    - gateway/oxlo: LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    """
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "mock":
        return _mock_questions(course, topic, difficulty, count)

    prompt = (
        "Generate JSON only. Create MCQs for an adaptive learning platform. "
        f"course={course}, topic={topic}, difficulty={difficulty}, count={count}. "
        "Return a list named questions with question, options, correct_answer, explanation."
    )

    if provider == "gemini":
        return _call_gemini(prompt)

    return _call_openai_compatible(prompt, provider)


def _call_openai_compatible(prompt: str, provider: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL")
    model = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini")
    if not api_key or not base_url:
        return {"provider": provider, "error": "Missing API key or base URL.", "questions": []}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    return _parse_llm_response(request, provider)


def _call_gemini(prompt: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    if not api_key:
        return {"provider": "gemini", "error": "Missing GEMINI_API_KEY.", "questions": []}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return _parse_llm_response(request, "gemini")


def _parse_llm_response(request, provider: str) -> dict:
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"provider": provider, "error": str(exc), "questions": []}

    text = json.dumps(raw)
    if "choices" in raw:
        text = raw["choices"][0]["message"]["content"]
    elif "candidates" in raw:
        text = raw["candidates"][0]["content"]["parts"][0]["text"]

    try:
        parsed = json.loads(text.strip().strip("`").replace("json\n", "", 1))
    except json.JSONDecodeError:
        return {"provider": provider, "raw": text, "questions": []}
    return {"provider": provider, "questions": parsed.get("questions", parsed)}


def _mock_questions(course: str, topic: str, difficulty: str, count: int) -> dict:
    questions = []
    for index in range(count):
        questions.append(
            {
                "question": f"What is a {difficulty} concept about {topic} in {course}?",
                "options": ["Correct concept", "Distractor one", "Distractor two", "Distractor three"],
                "correct_answer": "A",
                "explanation": f"This checks {topic} understanding at {difficulty} level.",
            }
        )
    return {"provider": "mock", "questions": questions}
