from pathlib import Path
import random

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "simulation_results"
GRAPH_FILES = {
    "proficiency_progression": "proficiency_progression.png",
    "random_vs_adaptive": "random_vs_adaptive.png",
    "confidence_trends": "confidence_trends.png",
}


def run_research_simulation(
    students_per_group: int = 8,
    session_length: int = 20,
) -> dict:
    """Run a lightweight comparison of random and adaptive assessment.

    Synthetic students are grouped by true proficiency. Each simulated response
    uses a simple probability model: students are more likely to answer correctly
    when their true proficiency is above the selected question difficulty.
    """
    RESULTS_DIR.mkdir(exist_ok=True)

    records = []
    for profile_name, true_proficiency in _student_profiles().items():
        for student_index in range(students_per_group):
            student_id = f"{profile_name}_{student_index + 1}"
            records.extend(
                _simulate_session(
                    mode="random",
                    student_id=student_id,
                    profile_name=profile_name,
                    true_proficiency=true_proficiency,
                    session_length=session_length,
                )
            )
            records.extend(
                _simulate_session(
                    mode="adaptive",
                    student_id=student_id,
                    profile_name=profile_name,
                    true_proficiency=true_proficiency,
                    session_length=session_length,
                )
            )

    results = pd.DataFrame(records)
    summary = _build_summary(results)
    graph_paths = _create_graphs(results)

    summary_path = RESULTS_DIR / "evaluation_summary.csv"
    summary["by_mode"].to_csv(summary_path, index=False)

    return {
        "message": "Simulation completed successfully.",
        "students_per_group": students_per_group,
        "session_length": session_length,
        "total_responses": int(len(results)),
        "graphs": graph_paths,
        "summary": summary["api_summary"],
    }


def get_graph_results() -> dict:
    """Return generated graph file paths for API consumers."""
    return {
        name: str(RESULTS_DIR / filename)
        for name, filename in GRAPH_FILES.items()
        if (RESULTS_DIR / filename).exists()
    }


def get_evaluation_summary() -> dict:
    """Fetch the latest summary created by the simulator."""
    summary_path = RESULTS_DIR / "evaluation_summary.csv"
    if not summary_path.exists():
        return {
            "message": "No simulation summary found. Run the simulator from /admin/research first.",
            "results": [],
        }

    summary = pd.read_csv(summary_path)
    return {
        "message": "Latest simulation summary loaded.",
        "results": summary.to_dict(orient="records"),
    }


def _simulate_session(
    mode: str,
    student_id: str,
    profile_name: str,
    true_proficiency: float,
    session_length: int,
) -> list[dict]:
    """Simulate one assessment session.

    Convergence means the estimated proficiency gradually moves closer to the
    student's hidden true proficiency as more answers are observed.
    """
    alpha = 1.0
    beta = 1.0
    records = []

    for step in range(1, session_length + 1):
        estimated_proficiency = alpha / (alpha + beta)
        uncertainty = 1 / (alpha + beta)
        difficulty = _select_difficulty(mode, estimated_proficiency)
        correctness = _sample_correctness(true_proficiency, difficulty)
        confidence = _sample_confidence(correctness, true_proficiency, difficulty)
        response_time = _sample_response_time(correctness, confidence, true_proficiency, difficulty)

        alpha, beta = _update_estimate(
            alpha=alpha,
            beta=beta,
            correctness=correctness,
            confidence=confidence,
            response_time=response_time,
            difficulty=difficulty,
        )
        updated_estimate = alpha / (alpha + beta)

        records.append(
            {
                "mode": mode,
                "student_id": student_id,
                "profile": profile_name,
                "true_proficiency": true_proficiency,
                "step": step,
                "difficulty": difficulty,
                "correctness": int(correctness),
                "confidence": confidence,
                "response_time": response_time,
                "estimated_proficiency": updated_estimate,
                "uncertainty": 1 / (alpha + beta),
                "absolute_error": abs(true_proficiency - updated_estimate),
            }
        )

    return records


def _select_difficulty(mode: str, estimated_proficiency: float) -> float:
    """Random mode explores blindly; adaptive mode targets current proficiency."""
    if mode == "random":
        return random.choice(_question_difficulties())

    sampled_target = np.random.normal(loc=estimated_proficiency, scale=0.12)
    return _nearest_difficulty(float(np.clip(sampled_target, 0.1, 0.9)))


def _sample_correctness(true_proficiency: float, difficulty: float) -> bool:
    probability = 0.15 + (0.75 / (1 + np.exp(-8 * (true_proficiency - difficulty))))
    return random.random() < probability


def _sample_confidence(
    correctness: bool,
    true_proficiency: float,
    difficulty: float,
) -> float:
    """Confidence rises when the task is well matched to ability and correct."""
    base = 0.45 + (true_proficiency - difficulty)
    if correctness:
        base += 0.2
    else:
        base -= 0.15
    return float(np.clip(np.random.normal(base, 0.12), 0.05, 0.95))


def _sample_response_time(
    correctness: bool,
    confidence: float,
    true_proficiency: float,
    difficulty: float,
) -> float:
    """Response time acts as a hesitation signal in the simulator."""
    challenge_gap = max(0.0, difficulty - true_proficiency)
    base_time = 18 + (35 * challenge_gap) + ((1 - confidence) * 20)
    if not correctness:
        base_time += 8
    return float(np.clip(np.random.normal(base_time, 5), 6, 75))


def _update_estimate(
    alpha: float,
    beta: float,
    correctness: bool,
    confidence: float,
    response_time: float,
    difficulty: float,
) -> tuple[float, float]:
    """Small Bayesian-style update matching the app's explainable logic."""
    speed_score = 1.0 if response_time <= 10 else max(0.0, (60 - response_time) / 50)
    evidence_weight = 0.5 + (0.3 * confidence) + (0.2 * speed_score)

    if correctness:
        alpha += evidence_weight * (0.5 + difficulty)
    else:
        beta += evidence_weight * (1.5 - difficulty)
    return alpha, beta


def _build_summary(results: pd.DataFrame) -> dict:
    final_rows = results.sort_values("step").groupby(["mode", "student_id"]).tail(1)
    by_mode = (
        final_rows.groupby("mode")
        .agg(
            final_absolute_error=("absolute_error", "mean"),
            final_uncertainty=("uncertainty", "mean"),
            adaptive_accuracy=("correctness", "mean"),
            final_estimated_proficiency=("estimated_proficiency", "mean"),
        )
        .reset_index()
    )

    return {
        "by_mode": by_mode,
        "api_summary": by_mode.round(4).to_dict(orient="records"),
    }


def _create_graphs(results: pd.DataFrame) -> dict:
    graph_paths = {}

    progression = (
        results.groupby(["mode", "step"])["estimated_proficiency"].mean().reset_index()
    )
    plt.figure(figsize=(8, 5))
    for mode, group in progression.groupby("mode"):
        plt.plot(group["step"], group["estimated_proficiency"], label=mode)
    plt.title("Average Proficiency Progression")
    plt.xlabel("Question Number")
    plt.ylabel("Estimated Proficiency")
    plt.legend()
    graph_paths["proficiency_progression"] = _save_graph("proficiency_progression")

    comparison = (
        results.groupby(["mode", "step"])[["absolute_error", "uncertainty"]]
        .mean()
        .reset_index()
    )
    plt.figure(figsize=(8, 5))
    for mode, group in comparison.groupby("mode"):
        plt.plot(group["step"], group["absolute_error"], label=f"{mode} error")
        plt.plot(group["step"], group["uncertainty"], linestyle="--", label=f"{mode} uncertainty")
    plt.title("Random vs Adaptive Comparison")
    plt.xlabel("Question Number")
    plt.ylabel("Lower is Better")
    plt.legend()
    graph_paths["random_vs_adaptive"] = _save_graph("random_vs_adaptive")

    confidence = results.groupby(["mode", "step"])["confidence"].mean().reset_index()
    plt.figure(figsize=(8, 5))
    for mode, group in confidence.groupby("mode"):
        plt.plot(group["step"], group["confidence"], label=mode)
    plt.title("Confidence Trends")
    plt.xlabel("Question Number")
    plt.ylabel("Average Confidence")
    plt.legend()
    graph_paths["confidence_trends"] = _save_graph("confidence_trends")

    return graph_paths


def _save_graph(graph_name: str) -> str:
    path = RESULTS_DIR / GRAPH_FILES[graph_name]
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    return str(path)


def _student_profiles() -> dict[str, float]:
    return {
        "low": 0.3,
        "medium": 0.55,
        "high": 0.8,
    }


def _question_difficulties() -> list[float]:
    return [0.2, 0.4, 0.6, 0.8]


def _nearest_difficulty(target: float) -> float:
    return min(_question_difficulties(), key=lambda difficulty: abs(difficulty - target))
