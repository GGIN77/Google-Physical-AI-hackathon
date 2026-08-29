from typing import Any

from .base_game import BaseGame


class KambaValiGame(BaseGame):
    """
    Game engine for Kamba Vali (Tug of War).

    The ESP32 detects the physical win condition using the IR
    sensors. The backend keeps track of the match result,
    rope movement, and useful statistics from the IMU.
    """

    def __init__(self):
        super().__init__("KAMBA_VALI")

        self.team_a_crossings = 0
        self.team_b_crossings = 0

        self.max_acceleration_g = 0.0
        self.average_acceleration_g = 0.0

        self.acceleration_samples = 0
        self.total_acceleration = 0.0

        self.last_ir_a = None
        self.last_ir_b = None

    # ---------------------------------------------------------
    # Reset game-specific data
    # ---------------------------------------------------------

    def reset_game_data(self) -> None:
        self.team_a_crossings = 0
        self.team_b_crossings = 0

        self.max_acceleration_g = 0.0
        self.average_acceleration_g = 0.0

        self.acceleration_samples = 0
        self.total_acceleration = 0.0

        self.last_ir_a = None
        self.last_ir_b = None

    # ---------------------------------------------------------
    # Start game
    # ---------------------------------------------------------

    def start_game(self) -> None:
        self.log_event(
            "MATCH_STARTED",
            {
                "game": "KAMBA_VALI"
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
        # Read acceleration
        # -----------------------------------------------------

        acceleration = self._safe_float(
            telemetry.get(
                "accel_magnitude_g"
            )
        )

        if acceleration is not None:

            self.acceleration_samples += 1

            self.total_acceleration += acceleration

            self.average_acceleration_g = (
                self.total_acceleration
                / self.acceleration_samples
            )

            if acceleration > self.max_acceleration_g:

                self.max_acceleration_g = acceleration

        # -----------------------------------------------------
        # Read IR sensors
        # -----------------------------------------------------

        ir_a = telemetry.get("ir_a")
        ir_b = telemetry.get("ir_b")

        # -----------------------------------------------------
        # Detect Team A crossing
        # -----------------------------------------------------

        if (
            ir_a == 0
            and self.last_ir_a == 1
            and not self.is_finished()
        ):

            self.team_a_crossings += 1

            self.log_event(
                "TEAM_A_CROSSED",
                {
                    "sensor": "IR_A",
                    "acceleration_g": acceleration,
                },
            )

        # -----------------------------------------------------
        # Detect Team B crossing
        # -----------------------------------------------------

        if (
            ir_b == 0
            and self.last_ir_b == 1
            and not self.is_finished()
        ):

            self.team_b_crossings += 1

            self.log_event(
                "TEAM_B_CROSSED",
                {
                    "sensor": "IR_B",
                    "acceleration_g": acceleration,
                },
            )

        self.last_ir_a = ir_a
        self.last_ir_b = ir_b

        # -----------------------------------------------------
        # Trust the ESP32's final winner
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
                    "max_acceleration_g":
                        self.max_acceleration_g,
                    "average_acceleration_g":
                        self.average_acceleration_g,
                },
            )

    # ---------------------------------------------------------
    # Safe float conversion
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
            "team_a_crossings":
                self.team_a_crossings,

            "team_b_crossings":
                self.team_b_crossings,

            "max_acceleration_g":
                round(
                    self.max_acceleration_g,
                    3,
                ),

            "average_acceleration_g":
                round(
                    self.average_acceleration_g,
                    3,
                ),

            "acceleration_samples":
                self.acceleration_samples,

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