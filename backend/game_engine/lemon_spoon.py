from typing import Any

from .base_game import BaseGame


class LemonSpoonGame(BaseGame):
    """
    Game engine for Lemon & Spoon.

    The ESP32 detects possible lemon drops using IMU jerk
    and detects the finish line using an IR sensor.

    The backend keeps track of:
    - Drop events
    - Finish events
    - Motion stability
    - Steadiness score
    - Final outcome
    """

    def __init__(self):
        super().__init__("LEMON_SPOON")

        self.drop_count = 0
        self.finish_detected = False

        self.total_jerk = 0.0
        self.jerk_samples = 0
        self.max_jerk_g = 0.0

        self.steadiness_score = 100.0

        self.last_drop_state = False
        self.last_finish_state = False

    # ---------------------------------------------------------
    # Reset
    # ---------------------------------------------------------

    def reset_game_data(self) -> None:
        self.drop_count = 0

        self.finish_detected = False

        self.total_jerk = 0.0
        self.jerk_samples = 0
        self.max_jerk_g = 0.0

        self.steadiness_score = 100.0

        self.last_drop_state = False
        self.last_finish_state = False

    # ---------------------------------------------------------
    # Start
    # ---------------------------------------------------------

    def start_game(self) -> None:
        self.log_event(
            "MATCH_STARTED",
            {
                "game": "LEMON_SPOON"
            },
        )

    # ---------------------------------------------------------
    # Telemetry Processing
    # ---------------------------------------------------------

    def process_telemetry(
        self,
        telemetry: dict[str, Any],
    ) -> None:

        # -----------------------------------------------------
        # Jerk
        # -----------------------------------------------------

        jerk = self._safe_float(
            telemetry.get("jerk_g")
        )

        if jerk is not None:

            self.jerk_samples += 1

            self.total_jerk += jerk

            if jerk > self.max_jerk_g:
                self.max_jerk_g = jerk

        # -----------------------------------------------------
        # Drop Detection
        # -----------------------------------------------------

        drop_detected = bool(
            telemetry.get(
                "drop_detected",
                False,
            )
        )

        # Detect only the transition:
        # False -> True
        if (
            drop_detected
            and not self.last_drop_state
        ):

            self.drop_count += 1

            self.log_event(
                "LEMON_DROPPED",
                {
                    "jerk_g": jerk,
                    "drop_number": self.drop_count,
                },
            )

        self.last_drop_state = drop_detected

        # -----------------------------------------------------
        # Finish Detection
        # -----------------------------------------------------

        finish_detected = bool(
            telemetry.get(
                "finish_detected",
                False,
            )
        )

        if (
            finish_detected
            and not self.last_finish_state
        ):

            self.finish_detected = True

            self.log_event(
                "FINISH_LINE_CROSSED",
                {
                    "drop_count": self.drop_count,
                },
            )

        self.last_finish_state = finish_detected

        # -----------------------------------------------------
        # Calculate Steadiness
        # -----------------------------------------------------

        self._update_steadiness(jerk)

        # -----------------------------------------------------
        # Read ESP32 result
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
                    "winner": self.winner,
                    "drop_count": self.drop_count,
                    "steadiness_score":
                        round(
                            self.steadiness_score,
                            2,
                        ),
                },
            )

    # ---------------------------------------------------------
    # Steadiness Score
    # ---------------------------------------------------------

    def _update_steadiness(
        self,
        jerk: float | None,
    ) -> None:

        if jerk is None:
            return

        # Small movements have little effect.
        if jerk <= 0.5:
            penalty = 0.0

        # Moderate movement.
        elif jerk <= 1.5:
            penalty = 0.2

        # Large movement.
        elif jerk <= 3.5:
            penalty = 0.8

        # Very large movement.
        else:
            penalty = 2.0

        self.steadiness_score -= penalty

        self.steadiness_score = max(
            0.0,
            min(
                100.0,
                self.steadiness_score,
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

        average_jerk = 0.0

        if self.jerk_samples > 0:

            average_jerk = (
                self.total_jerk
                / self.jerk_samples
            )

        return {
            "drop_count":
                self.drop_count,

            "finish_detected":
                self.finish_detected,

            "max_jerk_g":
                round(
                    self.max_jerk_g,
                    3,
                ),

            "average_jerk_g":
                round(
                    average_jerk,
                    3,
                ),

            "steadiness_score":
                round(
                    self.steadiness_score,
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