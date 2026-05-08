from dotenv import load_dotenv
from pathlib import Path
import os
from groq import Groq

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def critic_agent(document):

    instruction_letter = """
You are a strict senior Product Manager reviewing a PRD document.

Evaluate the document carefully based on:

1. Completeness
2. Clarity
3. Technical depth
4. Realism
5. Structure
6. Business understanding

Check whether these sections exist:
- Problem Statement
- Goals
- User Stories
- Technical Requirements
- Success Metrics
- Risks

Scoring Rules:
- 90-100 = excellent
- 75-89 = good but improvable
- 50-74 = weak
- below 50 = poor

Reject if:
- sections are missing
- explanations are vague
- technical details are weak
- goals are unrealistic

Respond EXACTLY in this format:

STATUS: approved OR rejected
SCORE: number out of 100
MISSING: missing sections or none
FEEDBACK: detailed improvement feedback
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": instruction_letter},
            {"role": "user", "content": document}
        ]
    )

    return response.choices[0].message.content