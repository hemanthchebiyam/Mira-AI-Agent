import os
from datetime import datetime
from openai import OpenAI
from .prompts import STATUS_REPORT_PROMPT, PROJECT_PLAN_PROMPT

class LLMHandler:
    def __init__(self, api_key=None, model="gpt-4o-mini"):
        self.model = model
        # Use passed api_key if available, otherwise fallback to env var
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def generate_status_report(self, trello_data):
        """Generate weekly status report from Trello data"""
        formatted_data = "\n".join([
            f"## {list_name}\n" + "\n".join(cards) 
            for list_name, cards in trello_data.items()
        ])
        
        current_date = datetime.now().strftime("%Y-%m-%d")
        prompt = STATUS_REPORT_PROMPT.format(trello_data=formatted_data, date=current_date)
        
        return self._call_llm(prompt, "You are a helpful Technical Program Manager assistant.")

    def generate_project_plan(self, documents_text):
        """Generate project plan from documents"""
        prompt = PROJECT_PLAN_PROMPT.format(documents_text=documents_text)
        return self._call_llm(prompt, "You are an expert Technical Program Manager.")

    def _call_llm(self, user_prompt, system_prompt):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
