from __future__ import annotations

TRIGGERS = [
    "triage_inbox",
    "morning_brief",
    "meeting_prep",
    "goal_drift",
    "weekly_review",
    "review_pr",
    "finance_anomaly",
    "relationship_nudge",
    "commitment_tracker",
    "followup_bot",
    "learning_synthesizer",
    "calendar_guard",
    "travel_prep",
    "task_rollup",
    "knowledge_digest",
    "risk_watch",
    "security_diff_scan",
    "model_cost_watch",
    "ops_regression_watch",
    "daily_compact",
]


def registered() -> list[str]:
    return TRIGGERS
