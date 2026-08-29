from typing import Any

from .base_game import BaseGame


class MusicalChairsGame(BaseGame):
    """
    Game engine for Musical Chairs.

    The ESP32 uses the HC-SR04 ultrasonic sensor to detect
    when a player reaches the chair after the music stops.

    The backend records:
    - Reaction time
    - Seating events
    - Reaction-time history
    - Reflex consistency
    - Final outcome
    """

    def __init__(self):
        super().__init__("MUSICAL_CHAIRS")

        self.reaction_time_ms: float | None = None

        self.reaction_times: list[float] = []

        self.seating_events = 0

        self.best_reaction_ms: float | None = None

        self.worst_reaction_ms: float | None = None

        self.average_reaction_ms: float | None = None

        self.consistency_score = 0.0

        self.last_reaction_time = None

        self.last_seated_state = False

    # ---------------------------------------------------------
    # Reset game-specific data
    # ---------------------------------------------------------

    def reset_game_data(self) -> None:
        self.reaction_time_ms = None

        self.reaction_times.clear()

        self.seating_events = 0

        self.best_reaction_ms = None

        self.worst_reaction_ms = None

        self.average_reaction_ms = None

        self.consistency_score = 0.0

        self.last_reaction_time = None

        self.last_seated_state = False

    # ---------------------------------------------------------
    # Start game
    # ---------------------------------------------------------

    def start_game(self) -> None:
        self.log_event(
            "MATCH_STARTED",
            {
                "game": "MUSICAL_CHAIRS"
            },
        )

    # ---------------------------------------------------------
    # Process telemetry
    # ---------------------------------------------------------

    def process_telemetry(
        self,
        telemetry: dict[str, Any],
    ) -> None:

        # -----------------------------------------------------
        # Read reaction time
        # -----------------------------------------------------

        reaction_time = self._safe_float(
            telemetry.get(
                "reaction_time_ms"
            )
        )

        if (
            reaction_time is not None
            and reaction_time >= 0
        ):

            # Only record a new value when it
            # differs from the previous one.

            if (
                self.last_reaction_time is None
                or reaction_time
                != self.last_reaction_time
            ):

                self.reaction_time_ms = (
                    reaction_time
                )

                self.reaction_times.append(
                    reaction_time
                )

                self.seating_events += 1

                self._update_statistics()

                self.log_event(
                    "PLAYER_SEATED",
                    {
                        "reaction_time_ms":
                            round(
                                reaction_time,
                                3,
                            ),

                        "attempt":
                            self.seating_events,
                    },
                )

                self.last_reaction_time = (
                    reaction_time
                )

        # -----------------------------------------------------
        # Read ESP32 winner
        # -----------------------------------------------------

        esp32_winner = telemetry.get(
            "winner"
        )

        if (
            esp32_winner
            and esp32_winner != ""
            and esp32_winner != self.winner
        ):

            self.winner = esp32_winner

            self.state = "RESULT"

            self.log_event(
                "MATCH_RESULT",
                {
                    "winner":
                        self.winner,

                    "reaction_time_ms":
                        self.reaction_time_ms,

                    "consistency_score":
                        round(
                            self.consistency_score,
                            2,
                        ),
                },
            )

    # ---------------------------------------------------------
    # Calculate reaction statistics
    # ---------------------------------------------------------

    def _update_statistics(self) -> None:

        if not self.reaction_times:
            return

        self.best_reaction_ms = min(
            self.reaction_times
        )

        self.worst_reaction_ms = max(
            self.reaction_times
        )

        self.average_reaction_ms = (
            sum(self.reaction_times)
            / len(self.reaction_times)
        )

        self.consistency_score = (
            self._calculate_consistency()
        )

    # ---------------------------------------------------------
    # Reflex Consistency
    # ---------------------------------------------------------

    def _calculate_consistency(self) -> float:

        if len(self.reaction_times) < 2:

            # A single reaction cannot really
            # measure consistency.

            return 100.0

        average = (
            sum(self.reaction_times)
            / len(self.reaction_times)
        )

        if average <= 0:
            return 0.0

        deviations = [
            abs(
                value - average
            )
            for value in self.reaction_times
        ]

        mean_deviation = (
            sum(deviations)
            / len(deviations)
        )

        # Convert variation into a 0-100 score.

        variation_ratio = (
            mean_deviation
            / average
        )

        score = (
            100.0
            - (
                variation_ratio
                * 100.0
            )
        )

        return max(
            0.0,
            min(
                100.0,
                score,
            ),
        )

    # ---------------------------------------------------------
    # Safe Float Conversion
    # ---------------------------------------------------------

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> float | None:

        if value is None:
            return None

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:

        return {
            "reaction_time_ms":
                (
                    round(
                        self.reaction_time_ms,
                        3,
                    )
                    if self.reaction_time_ms
                    is not None
                    else None
                ),

            "best_reaction_ms":
                (
                    round(
                        self.best_reaction_ms,
                        3,
                    )
                    if self.best_reaction_ms
                    is not None
                    else None
                ),

            "worst_reaction_ms":
                (
                    round(
                        self.worst_reaction_ms,
                        3,
                    )
                    if self.worst_reaction_ms
                    is not None
                    else None
                ),

            "average_reaction_ms":
                (
                    round(
                        self.average_reaction_ms,
                        3,
                    )
                    if self.average_reaction_ms
                    is not None
                    else None
                ),

            "seating_events":
                self.seating_events,

            "consistency_score":
                round(
                    self.consistency_score,
                    2,
                ),

            "winner":
                self.winner,

            "state":
                self.state,
        }

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    def get_result(self) -> dict[str, Any]:

        result = super().get_result()

        result["statistics"] = (
            self.get_statistics()
        )

        return result