from abc import ABC, abstractmethod
from collections import deque
from datetime import datetime
from typing import Any


class BaseGame(ABC):
    """
    Common interface for every Onakali Referee game.

    Each game receives telemetry from the ESP32 and decides
    what that telemetry means according to its own rules.
    """

    def __init__(self, game_name: str):
        self.game_name = game_name

        self.state = "IDLE"

        self.winner: str | None = None

        self.events: list[dict[str, Any]] = []

        # Keep a bounded telemetry history so memory usage
        # remains predictable during long matches.
        self.telemetry_history: deque[
            dict[str, Any]
        ] = deque(maxlen=200)

    # ---------------------------------------------------------
    # Reset
    # ---------------------------------------------------------

    def reset(self) -> None:
        """
        Reset the game to its initial state.
        """

        self.state = "IDLE"

        self.winner = None

        self.events.clear()

        self.telemetry_history.clear()

        self.reset_game_data()

    # ---------------------------------------------------------
    # Game-specific Reset
    # ---------------------------------------------------------

    @abstractmethod
    def reset_game_data(self) -> None:
        """
        Reset variables specific to the individual game.
        """

    # ---------------------------------------------------------
    # Start
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Start the game.
        """

        self.state = "IN_PROGRESS"

        self.winner = None

        self.events.clear()

        self.telemetry_history.clear()

        self.start_game()

    # ---------------------------------------------------------
    # Game-specific Start
    # ---------------------------------------------------------

    @abstractmethod
    def start_game(self) -> None:
        """
        Perform game-specific initialization.
        """

    # ---------------------------------------------------------
    # Telemetry
    # ---------------------------------------------------------

    def ingest_telemetry(
        self,
        telemetry: dict[str, Any],
    ) -> None:
        """
        Store telemetry and pass it to the game-specific
        processing logic.
        """

        self.telemetry_history.append(
            telemetry.copy()
        )

        self.state = telemetry.get(
            "state",
            self.state,
        )

        if telemetry.get("winner"):
            self.winner = telemetry["winner"]

        self.process_telemetry(
            telemetry
        )

    # ---------------------------------------------------------
    # Game-specific Telemetry Processing
    # ---------------------------------------------------------

    @abstractmethod
    def process_telemetry(
        self,
        telemetry: dict[str, Any],
    ) -> None:
        """
        Interpret telemetry according to game rules.
        """

    # ---------------------------------------------------------
    # Event Logging
    # ---------------------------------------------------------

    def log_event(
        self,
        event_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Record an important game event.
        """

        event = {
            "timestamp": datetime.now().isoformat(
                timespec="milliseconds"
            ),
            "game": self.game_name,
            "event": event_type,
            "details": details or {},
        }

        self.events.append(event)

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    def is_finished(self) -> bool:
        """
        Check whether the game has reached a result.
        """

        return (
            self.state == "RESULT"
            or self.winner is not None
        )

    # ---------------------------------------------------------
    # Result Summary
    # ---------------------------------------------------------

    def get_result(self) -> dict[str, Any]:
        """
        Return a standard result structure.
        """

        return {
            "game": self.game_name,
            "state": self.state,
            "winner": self.winner,
            "events": list(self.events),
        }

    # ---------------------------------------------------------
    # Telemetry History
    # ---------------------------------------------------------

    def get_telemetry_history(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return a copy of recent telemetry.
        """

        return list(
            self.telemetry_history
        )

    # ---------------------------------------------------------
    # Events
    # ---------------------------------------------------------

    def get_events(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return a copy of the event log.
        """

        return list(self.events)