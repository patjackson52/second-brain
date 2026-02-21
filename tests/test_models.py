import pytest
from pydantic import ValidationError

from models.triage import PARADestination, TriageBatch, TriageDecision


class TestPARADestination:
    def test_valid_destinations(self):
        assert PARADestination.PROJECTS_ACTIVE == "1_projects/active"
        assert PARADestination.AREAS == "2_areas"
        assert PARADestination.RESOURCES == "3_resources"
        assert PARADestination.ARCHIVE == "4_archive"
        assert PARADestination.PEOPLE == "5_people"

    def test_all_destinations_are_strings(self):
        for dest in PARADestination:
            assert isinstance(dest.value, str)


class TestTriageDecision:
    def test_valid_decision(self):
        decision = TriageDecision(
            filename="test-note.md",
            destination=PARADestination.AREAS,
            subdirectory="Health",
            confidence=0.85,
            reasoning="Ongoing health tracking",
            suggested_rename="health-checkup.md",
            tags=["health", "routine"],
        )
        assert decision.filename == "test-note.md"
        assert decision.destination == PARADestination.AREAS
        assert decision.confidence == 0.85

    def test_minimal_decision(self):
        decision = TriageDecision(
            filename="note.md",
            destination=PARADestination.ARCHIVE,
            subdirectory=None,
            confidence=0.9,
            reasoning="Old note",
            suggested_rename=None,
            tags=[],
        )
        assert decision.subdirectory is None
        assert decision.suggested_rename is None

    def test_confidence_bounds_low(self):
        with pytest.raises(ValidationError):
            TriageDecision(
                filename="note.md",
                destination=PARADestination.AREAS,
                subdirectory=None,
                confidence=-0.1,
                reasoning="test",
                suggested_rename=None,
                tags=[],
            )

    def test_confidence_bounds_high(self):
        with pytest.raises(ValidationError):
            TriageDecision(
                filename="note.md",
                destination=PARADestination.AREAS,
                subdirectory=None,
                confidence=1.1,
                reasoning="test",
                suggested_rename=None,
                tags=[],
            )

    def test_invalid_destination(self):
        with pytest.raises(ValidationError):
            TriageDecision(
                filename="note.md",
                destination="invalid_folder",
                subdirectory=None,
                confidence=0.5,
                reasoning="test",
                suggested_rename=None,
                tags=[],
            )


class TestTriageBatch:
    def test_valid_batch(self):
        batch = TriageBatch(
            decisions=[
                TriageDecision(
                    filename="note1.md",
                    destination=PARADestination.PROJECTS_ACTIVE,
                    subdirectory="hawaii-2026",
                    confidence=0.9,
                    reasoning="Has deadline and deliverable",
                    suggested_rename="hawaii-trip-planning.md",
                    tags=["travel", "project"],
                ),
            ],
            skipped=["binary-file.pdf"],
        )
        assert len(batch.decisions) == 1
        assert len(batch.skipped) == 1

    def test_empty_batch(self):
        batch = TriageBatch(decisions=[], skipped=[])
        assert len(batch.decisions) == 0

    def test_skipped_defaults_empty(self):
        batch = TriageBatch(decisions=[])
        assert batch.skipped == []
