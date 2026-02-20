from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PARADestination(str, Enum):
    PROJECTS_ACTIVE = "1_projects/active"
    PROJECTS_WAITING = "1_projects/waiting"
    AREAS = "2_areas"
    RESOURCES = "3_resources"
    ARCHIVE = "4_archive"
    PEOPLE = "5_people"


class TriageDecision(BaseModel):
    filename: str = Field(description="Original filename in 0_inbox/")
    destination: PARADestination = Field(description="Target PARA directory")
    subdirectory: Optional[str] = Field(
        default=None,
        description="Subdirectory within destination (e.g., 'Health' under 2_areas)",
    )
    confidence: float = Field(ge=0, le=1, description="Triage confidence 0.0-1.0")
    reasoning: str = Field(description="Explanation of routing decision")
    suggested_rename: Optional[str] = Field(
        default=None,
        description="Suggested canonical filename (lowercase-hyphenated.md)",
    )
    tags: list[str] = Field(default_factory=list, description="Suggested tags")


class TriageBatch(BaseModel):
    decisions: list[TriageDecision] = Field(description="Triage decisions for each file")
    skipped: list[str] = Field(
        default_factory=list,
        description="Filenames that could not be processed",
    )
