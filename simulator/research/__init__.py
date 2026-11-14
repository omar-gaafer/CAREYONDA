"""Research-only synthetic simulation extensions; separate from the core generator."""

from simulator.research.benign_exercise_control import (
    BenignExerciseControlConfig,
    ModelBResearchMission,
    ResearchLabel,
    ResearchScenario,
    generate_model_b_research_mission,
)

__all__ = [
    "BenignExerciseControlConfig",
    "ModelBResearchMission",
    "ResearchLabel",
    "ResearchScenario",
    "generate_model_b_research_mission",
]
