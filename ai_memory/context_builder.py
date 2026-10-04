from .models import AIMemory


class MemoryContextBuilder:
    """
    Builds long-term memory context for the AI.
    """

    def __init__(self, user):
        self.user = user

    def build(self) -> str:
        memories = (
            AIMemory.objects.filter(
                user=self.user
            )
            .order_by("-importance", "-updated_at")
        )

        if not memories.exists():
            return ""

        lines = [
            "LONG TERM USER MEMORY",
            "=====================",
        ]

        for memory in memories:

            lines.append(
                f"- [{memory.memory_type.upper()}] "
                f"{memory.key}: {memory.value}"
            )

        return "\n".join(lines)