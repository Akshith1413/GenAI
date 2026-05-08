from dotenv import load_dotenv
from pathlib import Path
import os
from groq import Groq

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def writer_agent(rough_notes):

    instruction_letter = """
    You are a professional Product Manager document writer.

    Your job is to take rough notes and turn them into a 
    full structured PRD document.

    Every document MUST have:
    1. Problem Statement
    2. Goals
    3. User Stories
    4. Technical Requirements
    5. Success Metrics
    6. Risks
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": instruction_letter},
            {"role": "user", "content": rough_notes}
        ]
    )

    return response.choices[0].message.content