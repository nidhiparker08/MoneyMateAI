from typing import List

from ..models import AIChatMessage


class MemoryService:
    """
    Handles retrieval of recent conversation history.
    """

    def __init__(self, user):
        self.user = user

    def get_recent_messages(self, limit: int = 10) -> List[AIChatMessage]:
        """
        Return the most recent chat messages.
        """

        return list(
            AIChatMessage.objects.filter(
                user=self.user,
                session_id="default",
            )
            .order_by("-created_at")[:limit]
        )[::-1]

    def build_history(self, limit: int = 10) -> str:
        """
        Convert recent messages into text for Gemini.
        """

        messages = self.get_recent_messages(limit)

        if not messages:
            return ""

        history = []

        for message in messages:
            history.append(
                f"{message.role.upper()}: {message.content}"
            )

        return "\n".join(history)