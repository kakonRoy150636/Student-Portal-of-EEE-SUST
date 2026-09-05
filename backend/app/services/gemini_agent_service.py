from app.integrations.gemini_client import generate_gemini_response

class GeminiAgentService:
    def generate_study_plan(self, topics: list[str], days: int):
        prompt = f"Create a daily revision roadmap for EEE topics: {topics} over {days} days."
        return generate_gemini_response(prompt)
