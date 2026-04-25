from __future__ import annotations

# Strict rubric weights
AI_HIRING_WEIGHT = 0.4
AI_LEADERSHIP_WEIGHT = 0.4
GITHUB_ACTIVITY_WEIGHT = 0.2
EXECUTIVE_COMMENTARY_WEIGHT = 0.2
ML_STACK_WEIGHT = 0.1
STRATEGIC_COMM_WEIGHT = 0.1

SIGNAL_WEIGHTS: dict[str, float] = {
    "ai_hiring": AI_HIRING_WEIGHT,
    "ai_leadership": AI_LEADERSHIP_WEIGHT,
    "github_activity": GITHUB_ACTIVITY_WEIGHT,
    "executive_commentary": EXECUTIVE_COMMENTARY_WEIGHT,
    "ml_stack": ML_STACK_WEIGHT,
    "strategic_comm": STRATEGIC_COMM_WEIGHT,
}

MAX_WEIGHTED_SUM = sum(SIGNAL_WEIGHTS.values())
SCORE_SCALE = 3.0 / MAX_WEIGHTED_SUM if MAX_WEIGHTED_SUM > 0 else 1.0

