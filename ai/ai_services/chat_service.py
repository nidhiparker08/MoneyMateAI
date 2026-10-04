import os
import time

from dotenv import load_dotenv
from google import genai

from .prompt_builder import PromptBuilder

load_dotenv()


class ChatService:
    """
    Handles all communication with the Gemini API.
    """

    # Tried in order after the primary model fails, so a quota hit or a
    # temporary capacity spike on one model doesn't break the chatbot.
    FALLBACK_MODELS = ("gemini-3.7-flash", "gemini-3.5-flash")

    # Substrings of error messages that are worth retrying once before
    # moving to the next model (rate limits / capacity spikes).
    TRANSIENT_MARKERS = (
        "429",
        "500",
        "503",
        "RESOURCE_EXHAUSTED",
        "UNAVAILABLE",
        "DEADLINE_EXCEEDED",
        "INTERNAL_ERROR",
    )

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found.")

        self.client = genai.Client(api_key=self.api_key)

        # Stable Gemini flash model available to this API key.
        # gemini-3.6-flash returns 429 (quota exhausted) on this plan;
        # override via GEMINI_MODEL in .env if needed.
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    def _candidate_models(self):
        models = [self.model]
        for model in self.FALLBACK_MODELS:
            if model not in models:
                models.append(model)
        return models

    def _generate(self, prompt: str) -> str:
        """
        Call Gemini with one retry per model and fallback across models.
        Raises the last error if every candidate fails.
        """
        last_error = None

        for model in self._candidate_models():
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                    )

                    if hasattr(response, "text") and response.text:
                        return response.text.strip()

                    last_error = RuntimeError("Gemini returned an empty response.")

                except Exception as exc:
                    last_error = exc
                    message = str(exc)
                    transient = any(marker in message for marker in self.TRANSIENT_MARKERS)

                    # Retry rate limits / capacity spikes once, then fall
                    # through to the next model (also handles 404s and
                    # permanent quota errors quickly).
                    if transient and attempt == 0:
                        time.sleep(1.5)
                        continue
                    break

        raise last_error

    def generate_response(
        self,
        user,
        user_message: str,
    ) -> str:
        """
        Generate a response using Gemini.
        """

        system_prompt, user_prompt = PromptBuilder.build(
            user,
            user_message
        )

        prompt = f"""
        {system_prompt}

        ----------------------------------------

        USER MESSAGE

        {user_prompt}
"""

        return self._generate(prompt)

    def health_check(self) -> bool:
        """
        Checks whether Gemini is reachable.
        """

        try:
            self._generate("Reply only with OK.")
            return True

        except Exception:
            return False