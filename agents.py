"""Agent configurations using Groq LLMs with programmatic guardrails."""

import os
import re
import json
from typing import Dict, Any, List, Tuple
from groq import Groq
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()

from models import CriticFeedback, DocumentState
from prompts import get_writer_prompt, get_critic_prompt

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Model configurations - Groq free-tier models for professional document quality
# Writer: 70B versatile model for sophisticated vocabulary (legal/consulting documents)
WRITER_MODEL = "llama-3.3-70b-versatile"
# Critic: Same 70B model with distinct prompts for high reasoning accuracy
CRITIC_MODEL = "llama-3.3-70b-versatile"


# ============================================================
# PROGRAMMATIC FABRICATION DETECTOR (Code-based guardrails)
# These run AFTER the LLM Critic and override its score when
# hallucination patterns are detected. Prompts alone are not
# reliable enough to enforce strict factual grounding.
# ============================================================

def _extract_numbers(text: str) -> set:
    """Extract all meaningful numbers and percentages from text."""
    # Match percentages like 25%, 3.2%, etc.
    percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
    # Match dollar amounts like $12, $18,000, $1.50
    dollars = re.findall(r'\$\s*([\d,]+(?:\.\d+)?)', text)
    # Match standalone numbers > 10 (skip list numbering like 1. 2. 3.)
    standalone = re.findall(r'(?<!\.)(?<!\w)(\d{2,}(?:,\d{3})*(?:\.\d+)?)(?!\w)(?!\.)', text)

    all_nums = set()
    for p in percentages:
        all_nums.add(f"{p}%")
    for d in dollars:
        all_nums.add(f"${d}")
    for s in standalone:
        clean = s.replace(',', '')
        try:
            if float(clean) > 10:
                all_nums.add(s)
        except ValueError:
            pass
    return all_nums


def _detect_source_type(source: str) -> str:
    """Detect what type of document the source material actually is."""
    source_lower = source.lower()

    type_signals = {
        "meeting_minutes": ["meeting", "attendees", "attended", "agenda", "action items",
                           "discussed", "sync", "standup", "next meeting", "minutes"],
        "report": ["quarter", "q1 ", "q2 ", "q3 ", "q4 ", "performance", "revenue",
                   "leads generated", "year-over-year", "metrics", "kpi", "report",
                   "findings", "analysis", "growth", "decline"],
        "memo": ["memo", "to:", "from:", "subject:", "policy", "effective immediately",
                "notice", "announcement", "directive"],
        "proposal": ["propose", "proposal", "budget request", "project plan", "rfp",
                    "scope of work", "deliverables", "timeline", "cost estimate"],
        "prd": ["feature", "user story", "requirement", "acceptance criteria",
                "sprint", "product requirement", "use case", "problem statement",
                "goals", "roadmap", "vision", "persona", "mvp", "backlog",
                "functional requirement", "non-functional", "wireframe"]
    }

    scores = {}
    for stype, signals in type_signals.items():
        scores[stype] = sum(1 for s in signals if s in source_lower)

    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] >= 2 else "unknown"


def programmatic_validation(draft: str, source: str, document_type: str) -> Dict[str, Any]:
    """
    Run code-based checks on the draft against source material.
    Returns penalties, flags, and suggestions that override the LLM Critic.
    """
    penalties = 0
    flags = []
    suggestions = []

    source_lower = source.lower()
    draft_lower = draft.lower()

    # ── CHECK 1: Word Count Ratio (Content Inflation) ──
    # Only penalize if source has enough substance (>50 words).
    # For very short notes (e.g., 20 words), a 5x increase to 100 words
    # is actually normal for professional formatting.
    source_words = len(source.split())
    draft_words = len(draft.split())
    ratio = draft_words / max(source_words, 1)

    if source_words > 50 and ratio > 5:
        penalties += 25
        flags.append(
            f"CONTENT INFLATION: Draft is {ratio:.1f}x longer than source "
            f"({draft_words} vs {source_words} words) — high hallucination risk"
        )
        suggestions.append("Drastically reduce draft length — only include information from the source")
    elif source_words > 50 and ratio > 3:
        penalties += 15
        flags.append(
            f"CONTENT INFLATION: Draft is {ratio:.1f}x longer than source "
            f"({draft_words} vs {source_words} words) — moderate hallucination risk"
        )
        suggestions.append("Reduce draft content to closely match source material")
    elif source_words <= 50 and ratio > 8:
        # For very sparse input, only flag extreme inflation
        penalties += 20
        flags.append(
            f"CONTENT INFLATION: Draft is {ratio:.1f}x longer than sparse source "
            f"({draft_words} vs {source_words} words) — likely contains fabricated content"
        )
        suggestions.append("Source is too brief for this much output — reduce to source facts only")

    # ── CHECK 2: Fabricated Numbers & Percentages ──
    source_nums = _extract_numbers(source)
    draft_nums = _extract_numbers(draft)
    fabricated_nums = draft_nums - source_nums

    for num in fabricated_nums:
        if '%' in num:
            penalties += 15
            flags.append(f"FABRICATED STATISTIC: '{num}' found in draft but NOT in source material")
        elif '$' in num:
            penalties += 10
            flags.append(f"FABRICATED AMOUNT: '{num}' found in draft but NOT in source material")
        else:
            penalties += 5
            flags.append(f"FABRICATED NUMBER: '{num}' found in draft but NOT in source material")

    if fabricated_nums:
        suggestions.append(
            f"Remove {len(fabricated_nums)} fabricated number(s)/statistic(s) not present in source"
        )

    # ── CHECK 3: Document Type Mismatch ──
    detected_type = _detect_source_type(source)
    if detected_type != "unknown" and detected_type != document_type:
        penalties += 20
        flags.append(
            f"TYPE MISMATCH: Source material appears to be '{detected_type}' "
            f"but document was requested as '{document_type}'"
        )
        suggestions.append(
            f"Change document type to '{detected_type}' to match the source material"
        )

    # ── CHECK 4: Wrong Sections for Document Type ──
    type_forbidden_keywords = {
        "report": ["user stories", "as a user,", "as a manager,", "edge cases",
                   "error handling", "user personas", "acceptance criteria"],
        "meeting_minutes": ["user stories", "as a user,", "edge cases",
                           "roi analysis", "implementation plan"],
        "memo": ["user stories", "as a user,", "edge cases",
                "technical specifications", "sprint"],
        "proposal": ["meeting minutes", "attendees list", "meeting date"],
        "prd": []  # PRD can contain anything if source supports it
    }

    forbidden = type_forbidden_keywords.get(document_type, [])
    found_forbidden = []
    for keyword in forbidden:
        if keyword in draft_lower:
            found_forbidden.append(keyword)

    if found_forbidden:
        penalties += len(found_forbidden) * 10
        flags.append(
            f"WRONG SECTIONS: Found [{', '.join(found_forbidden)}] in draft — "
            f"not appropriate for document type '{document_type}'"
        )
        suggestions.append(f"Remove sections not relevant to a '{document_type}' document")

    # ── CHECK 5: Placeholder Count ──
    placeholder_count = len(re.findall(r'\[.*?TBD.*?\]', draft, re.IGNORECASE))

    if placeholder_count >= 5:
        penalties += 30
        flags.append(f"EXCESSIVE PLACEHOLDERS: {placeholder_count} '[TBD]' placeholders — document lacks substance")
    elif placeholder_count >= 3:
        penalties += 20
        flags.append(f"MANY PLACEHOLDERS: {placeholder_count} '[TBD]' placeholders found")
    elif placeholder_count > 0:
        penalties += placeholder_count * 5
        flags.append(f"PLACEHOLDERS: {placeholder_count} '[TBD]' placeholder(s) found")

    # ── CHECK 6: Sparse Source ──
    if source_words < 50:
        penalties += 15
        flags.append(
            f"SOURCE TOO SPARSE: Only {source_words} words in source — "
            f"insufficient for a complete '{document_type}' document"
        )
        suggestions.append("User must provide more detailed source material")

    # Cap total penalties at 80 (so minimum score can't go below ~0)
    return {
        "penalties": min(penalties, 80),
        "flags": flags,
        "suggestions": suggestions
    }


# ============================================================
# AGENT FUNCTIONS
# ============================================================

def writer_agent(state: DocumentState, document_type: str) -> str:
    """
    Writer agent: Transforms raw input into structured markdown.
    Returns the formatted document content.
    """
    system_prompt = get_writer_prompt(document_type)

    # Build the user message
    if state.critique and not state.critique.passed:
        # Revision mode: include previous draft and critique feedback
        user_message = f"""Previous Draft:
{state.current_draft}

Critique Feedback:
- Score: {state.critique.score}/100
- Issues to address: {', '.join(state.critique.missing_elements)}
- Suggestions: {', '.join(state.critique.improvement_suggestions)}

Please revise the document to address ALL feedback. Output the complete revised markdown document."""
    else:
        # Initial draft mode
        user_message = f"""Transform the following messy notes into a professional {document_type}.

Raw Input:
{state.raw_input}

Output a complete, properly formatted markdown document."""

    response = groq_client.chat.completions.create(
        model=WRITER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        max_tokens=4096
    )

    return response.choices[0].message.content.strip()


def critic_agent(document: str, source_input: str, document_type: str) -> CriticFeedback:
    """
    Critic agent: Evaluates document quality and returns structured feedback.
    Combines LLM-based critique with programmatic guardrails.
    Returns a CriticFeedback object.
    """
    system_prompt = get_critic_prompt(document_type)

    user_message = f"""Evaluate the following document against the source material.

Source Material:
{source_input}

Document to Evaluate:
{document}

Provide your evaluation as a JSON object with the exact structure specified in your instructions."""

    response = groq_client.chat.completions.create(
        model=CRITIC_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,
        max_tokens=2048,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content

    try:
        parsed = json.loads(content)
        llm_score = parsed.get("score", 0)
        llm_passed = parsed.get("passed", False)
        llm_missing = parsed.get("missing_elements", [])
        llm_suggestions = parsed.get("improvement_suggestions", [])
    except (json.JSONDecodeError, KeyError) as e:
        llm_score = 0
        llm_passed = False
        llm_missing = ["Failed to parse critique output"]
        llm_suggestions = [f"Parse error: {str(e)}"]

    # ── PROGRAMMATIC GUARDRAILS: Override LLM if fabrication detected ──
    validation = programmatic_validation(document, source_input, document_type)

    # Apply penalties to the LLM score
    final_score = max(0, llm_score - validation["penalties"])

    # Merge flags into missing_elements
    all_missing = llm_missing + validation["flags"]
    all_suggestions = llm_suggestions + validation["suggestions"]

    # Force fail if programmatic checks found issues
    final_passed = llm_passed and final_score >= 90 and len(validation["flags"]) == 0

    return CriticFeedback(
        score=final_score,
        passed=final_passed,
        missing_elements=all_missing,
        improvement_suggestions=all_suggestions
    )
