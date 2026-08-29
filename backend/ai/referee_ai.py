import json
from typing import Any

import requests

from .prompts import get_prompt


class RefereeAI:
    """
    Local AI commentary engine for Onakali Referee.

    Uses Ollama running locally with the Gemma 2B model.

    Ollama endpoint:
        http://localhost:11434/api/generate
    """

    def __init__(
        self,
        model: str = "gemma2:2b",
        ollama_url: str = (
            "http://localhost:11434/api/generate"
        ),
        timeout: int = 60,
    ):
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout

        # Maximum telemetry entries sent to the model.
        self.max_log_entries = 200

    # ---------------------------------------------------------
    # Generate Commentary
    # ---------------------------------------------------------

    def generate_commentary(
        self,
        game_mode: str,
        telemetry: list[dict[str, Any]],
        result: dict[str, Any] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Generate referee commentary from recent telemetry.

        Only the last 200 telemetry entries are supplied to
        the model to keep inference predictable.
        """

        recent_telemetry = telemetry[
            -self.max_log_entries:
        ]

        recent_events = (
            events[-self.max_log_entries:]
            if events
            else []
        )

        match_data = {
            "game_mode": game_mode,
            "telemetry": recent_telemetry,
            "events": recent_events,
            "result": result or {},
        }

        serialized_data = json.dumps(
            match_data,
            indent=2,
            default=str,
        )

        prompt = get_prompt(
            game_mode,
            serialized_data,
        )

        return self._generate(prompt)

    # ---------------------------------------------------------
    # Ollama Request
    # ---------------------------------------------------------

    def _generate(
        self,
        prompt: str,
    ) -> str:
        """
        Send a generation request to the local Ollama server.
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        try:

            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=self.timeout,
            )

        except requests.exceptions.ConnectionError:

            return (
                "Referee AI is unavailable. "
                "Please make sure Ollama is running "
                "and the Gemma 2B model is installed."
            )

        except requests.exceptions.Timeout:

            return (
                "Referee AI took too long to respond. "
                "Please try again."
            )

        except requests.RequestException as error:

            return (
                "Referee AI connection error: "
                f"{error}"
            )

        # -----------------------------------------------------
        # HTTP Error
        # -----------------------------------------------------

        if not response.ok:

            return (
                "Ollama returned an error "
                f"(HTTP {response.status_code})."
            )

        # -----------------------------------------------------
        # Parse Response
        # -----------------------------------------------------

        try:

            data = response.json()

        except ValueError:

            return (
                "Referee AI returned an invalid response."
            )

        generated_text = data.get(
            "response"
        )

        if not generated_text:

            return (
                "Referee AI did not return any commentary."
            )

        return str(
            generated_text
        ).strip()

    # ---------------------------------------------------------
    # Check Ollama
    # ---------------------------------------------------------

    def is_available(self) -> bool:
        """
        Check whether the local Ollama service is reachable.
        """

        try:

            response = requests.get(
                "http://localhost:11434",
                timeout=3,
            )

            return response.ok

        except requests.RequestException:

            return False

    # ---------------------------------------------------------
    # Check Model
    # ---------------------------------------------------------

    def is_model_available(self) -> bool:
        """
        Check whether the configured model exists in Ollama.
        """

        try:

            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5,
            )

            if not response.ok:
                return False

            data = response.json()

            models = data.get(
                "models",
                [],
            )

            for model in models:

                model_name = model.get(
                    "name",
                    "",
                )

                if (
                    model_name == self.model
                    or model_name.startswith(
                        self.model + ":"
                    )
                ):
                    return True

            return False

        except (
            requests.RequestException,
            ValueError,
        ):

            return False