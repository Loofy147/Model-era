
# --- AI CLIENT CLASS ---
class AIClient:
    def __init__(self):
        try:
            from openai import OpenAI
            self.client = OpenAI()
            self.model = "gpt-4o"
            self.available = True
        except ImportError:
            print("❌ OpenAI library not found. Run `pip install openai`.")
            self.available = False
        except Exception as e:
            print(f"❌ API Error: {e}")
            self.available = False

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if not self.available:
            return " [MOCK OUTPUT: API Key Missing or Library not installed] "

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error calling API: {e}"
