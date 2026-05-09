from dotenv import load_dotenv
from pathlib import Path
import os
from groq import Groq

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def writer_agent(topic, input_text):
    instruction_letter = f"""
    You are a professional writer, analyst, and expert in your field.
    
    Your job is to take the provided input (rough notes, feedback, or instructions) 
    and write/improve a comprehensive, well-structured document about: {topic}.

    If the input contains 'Critic Feedback', you MUST use that feedback to improve the previous version of the document.
    
    CRITICAL INSTRUCTIONS TO EVADE AI DETECTION (ZERO PERCENT AI):
    - Write with maximum "burstiness" and "perplexity". 
    - Sentence structures must be extremely varied. Short punchy fragments. Followed by long, flowing, deeply analytical sentences.
    - Zero usage of AI tells: "In conclusion", "It is crucial", "Let's dive in", "Furthermore", "Moreover", "Delve", "Tapestry".
    - Adopt an idiosyncratic, slightly imperfect human voice. Use unique analogies, occasional conversational phrases, and highly specific expert vocabulary.
    - It must absolutely score 0% on ZeroGPT, Turnitin, and all AI detectors.
    
    Ensure the content is detailed, logical, and professionally structured with appropriate headings, while strictly enforcing this deeply natural human tone.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": instruction_letter},
            {"role": "user", "content": input_text}
        ],
        temperature=0.95,
        top_p=0.95,
        frequency_penalty=0.5,
        presence_penalty=0.5
    )

    return response.choices[0].message.content