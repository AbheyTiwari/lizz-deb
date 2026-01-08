import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from google import genai

load_dotenv()


class LLM:
    def __init__(
        self,
        model: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        temperature: float = os.environ.get("GEMINI_TEMPERATURE", 0.7),
    ):
        api_key = os.environ["GEMINI_API_KEY"]
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment")

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def generate(self, user_prompt: str, system_prompt: str | None = None) -> str:
        if system_prompt:
            prompt = f"{system_prompt}\n\nUser:\n{user_prompt}"
        else:
            prompt = user_prompt

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "temperature": self.temperature,
            },
        )

        return response.text.strip()
