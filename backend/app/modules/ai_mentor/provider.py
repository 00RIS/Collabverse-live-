import asyncio
from abc import ABC, abstractmethod

from google import genai
from google.genai import types

from app.core.config import settings


class AIProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: str,
        history: list[dict] | None = None,
    ) -> str:
        pass


class GeminiAIProvider(AIProvider):
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        self.model = "gemini-3.6-flash"

    def _build_history(
        self,
        history: list[dict] | None,
    ) -> list[types.Content]:

        gemini_history = []

        for message in history or []:
            role = message.get("role")

            if role == "assistant":
                gemini_role = "model"
            elif role == "user":
                gemini_role = "user"
            else:
                continue

            gemini_history.append(
                types.Content(
                    role=gemini_role,
                    parts=[
                        types.Part(
                            text=message.get("content", "")
                        )
                    ],
                )
            )

        return gemini_history

    def _generate_sync(
        self,
        system_prompt: str,
        user_message: str,
        context: str,
        history: list[dict] | None,
    ) -> str:

        full_system_prompt = f"""
{system_prompt}

USER CONTEXT:
{context}
"""

        chat = self.client.chats.create(
            model=self.model,
            history=self._build_history(history),
            config=types.GenerateContentConfig(
                system_instruction=full_system_prompt,
                temperature=0.7,
                max_output_tokens=1500,
            ),
        )

        response = chat.send_message(
            message=user_message
        )

        if not response.text:
            return "I couldn't generate a response. Please try again."

        return response.text

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        context: str,
        history: list[dict] | None = None,
    ) -> str:

        try:
            return await asyncio.to_thread(
                self._generate_sync,
                system_prompt,
                user_message,
                context,
                history,
            )

        except Exception as exc:
            print(f"Gemini provider error: {exc}")

            raise RuntimeError(
                "AI Mentor could not generate a response."
            ) from exc