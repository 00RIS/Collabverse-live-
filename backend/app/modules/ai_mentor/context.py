from typing import Any


class AIMentorContextBuilder:

    @staticmethod
    def build_basic_context(user: Any) -> dict:

        return {
            "user_id": str(
                getattr(user, "id", "")
            ),

            "email": getattr(
                user,
                "email",
                None
            ),

            "role": str(
                getattr(
                    user,
                    "role",
                    "unknown"
                )
            )
        }


    @staticmethod
    def context_to_text(context: dict) -> str:

        lines = [
            "USER CONTEXT"
        ]

        for key, value in context.items():

            if value is not None:
                lines.append(
                    f"{key}: {value}"
                )

        return "\n".join(lines)