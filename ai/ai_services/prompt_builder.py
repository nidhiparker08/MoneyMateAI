from ..services import (
    build_system_message,
)
from .memory_service import MemoryService
from ai_memory.context_builder import MemoryContextBuilder


class PromptBuilder:
    """
    Responsible for constructing the final prompt
    that is sent to Gemini.
    """

    @staticmethod
    def build(user, user_message: str) -> tuple[str, str]:
        """
        Returns:
            system_prompt,
            user_prompt
        """

        system_prompt = build_system_message(user)

        memory = MemoryService(user)

        history = memory.build_history()

        memory_context = MemoryContextBuilder(user).build()

        user_prompt = f"""
        LONG TERM MEMORY

        {memory_context}

        ----------------------------------------

        PREVIOUS CONVERSATION

        {history}

        ----------------------------------------

        CURRENT USER MESSAGE

        {user_message.strip()}
        """

        return system_prompt, user_prompt