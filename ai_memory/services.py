import json
import os
import re
from typing import List

from dotenv import load_dotenv
from google import genai

from .models import AIMemory, MemoryExtractionLog

load_dotenv()


class MemoryService:
    """
    Handles extraction, storage and retrieval
    of long-term AI memories.
    """

    SIMPLE_PATTERNS = [
        "i want",
        "i prefer",
        "i like",
        "i love",
        "i hate",
        "my salary",
        "my income",
        "i earn",
        "i am",
        "i'm",
        "my goal",
        "my dream",
        "i plan",
        "i will",
    ]

    def __init__(self):

        self.client = genai.Client(
            api_key=os.getenv("GEMINI_API_KEY")
        )

        self.model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    # ----------------------------------------------------

    def should_extract(self, message: str) -> bool:
        """
        Decide whether this message
        contains useful long-term information.
        """

        msg = message.lower()

        return any(
            pattern in msg
            for pattern in self.SIMPLE_PATTERNS
        )

    # ----------------------------------------------------

    def extract_local(self, message: str) -> List[dict]:
        """
        Fast local extraction.

        No Gemini API call.
        """

        memories = []

        salary = re.search(r"(?:salary|income|earn).*?(\d+)", message.lower())

        if salary:

            memories.append({

                "memory_type": "financial",

                "key": "monthly_income",

                "value": int(salary.group(1)),

                "importance": 10,

            })

        return memories

    # ----------------------------------------------------

    def extract_with_gemini(self, message: str):

        prompt = f"""
Extract ONLY long-term memories.

Ignore temporary conversations.

Return ONLY JSON.

Example:

[
  {{
    "memory_type":"goal",
    "key":"dream_vehicle",
    "value":"BMW GS1300",
    "importance":10
  }}
]

Message:

{message}
"""

        response = self.client.models.generate_content(

            model=self.model,

            contents=prompt

        )

        return json.loads(response.text)

    # ----------------------------------------------------

    def save_memory(self, user, memory: dict):

        obj, created = AIMemory.objects.update_or_create(

            user=user,

            memory_type=memory["memory_type"],

            key=memory["key"],

            defaults={

                "value": memory["value"],

                "importance": memory.get("importance", 5),

                "confidence": 100,

                "source": "conversation",

            }

        )

        return obj

    # ----------------------------------------------------

    def process(self, user, message: str):

        if not self.should_extract(message):

            return

        memories = self.extract_local(message)

        if not memories:

            try:

                memories = self.extract_with_gemini(message)

            except Exception:

                return

        for memory in memories:

            self.save_memory(user, memory)

            MemoryExtractionLog.objects.create(

                user=user,

                message=message,

                extracted_memory=memory,

                status="accepted",

                model_used=self.model,

            )