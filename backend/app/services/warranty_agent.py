"""
Chat-style warranty agent endpoint.

POST /agent/query
  Accepts a natural-language query from the user (e.g. "When does my
  laptop warranty expire?") and returns an LLM-generated answer based on
  the user's actual purchase records from the database.

Design:
  - The LLM is given a condensed JSON representation of the user's purchases
    (not raw email text) to keep the context small and private.
  - The Gemini 1.5 Flash model is used (same as the extraction fallback).
  - If no Gemini key is configured, returns a polite "not available" message.
  - Answers are in plain English (or Hindi if the user writes in Hindi).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models import Purchase

load_dotenv()

logger = logging.getLogger(__name__)

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_MODEL = "gemini-1.5-flash"

_SYSTEM_PROMPT = """\
You are Warranty Radar, a helpful personal warranty and purchase assistant.
You have access to the user's purchase records below.
Answer the user's question concisely and accurately based ONLY on these records.
If the answer is not in the records, say so clearly — do not guess.
Always mention specific product names and dates when relevant.
Keep answers under 150 words unless the user asks for detail.
If the user writes in Hindi or Hinglish, respond in the same language.
"""


def _build_purchase_context(db: Session, user_id) -> str:
    """
    Build a compact JSON summary of the user's purchases for the LLM context.
    Includes only fields relevant to warranty queries.
    """
    purchases = db.query(Purchase).filter(Purchase.user_id == user_id).all()

    if not purchases:
        return "[]"

    records = []
    for p in purchases:
        warranty = p.warranty_period
        record: dict = {
            "product": p.product_name or "Unknown product",
            "brand": p.brand,
            "retailer": p.retailer,
            "purchase_date": p.purchase_date.isoformat() if p.purchase_date else None,
            "price_inr": float(p.price) if p.price else None,
            "source": p.source_type,
        }
        if warranty:
            record["warranty_end"] = (
                warranty.warranty_end_date.isoformat()
                if warranty.warranty_end_date else None
            )
            record["return_window_end"] = (
                warranty.return_window_end_date.isoformat()
                if warranty.return_window_end_date else None
            )
            record["confidence"] = warranty.confidence_score
            record["is_estimated"] = warranty.is_estimated

        records.append(record)

    return json.dumps(records, ensure_ascii=False, indent=2)


def answer_query(db: Session, user_id, question: str) -> str:
    """
    Answer a natural-language warranty query for a user.

    Args:
        db: SQLAlchemy session.
        user_id: UUID of the user.
        question: The user's natural-language question.

    Returns:
        Plain-text answer string.
    """
    if not _GEMINI_API_KEY:
        return (
            "The AI assistant is not configured. "
            "Please set the GEMINI_API_KEY environment variable to enable this feature."
        )

    purchase_context = _build_purchase_context(db, user_id)
    today_str = date.today().isoformat()

    prompt = f"""{_SYSTEM_PROMPT}

Today's date: {today_str}

User's purchase records:
{purchase_context}

User's question: {question}

Answer:"""

    try:
        import google.generativeai as genai

        genai.configure(api_key=_GEMINI_API_KEY)
        model = genai.GenerativeModel(_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=400,
            ),
        )
        answer = response.text.strip() if response.text else ""
        if not answer:
            return "I could not generate an answer. Please try rephrasing your question."

        logger.info(
            "Agent query answered for user %s: %r → %d chars",
            user_id,
            question[:60],
            len(answer),
        )
        return answer

    except Exception as exc:
        logger.error("Agent query failed: %s", exc)
        return (
            "Sorry, I encountered an error while looking up your warranty information. "
            "Please try again in a moment."
        )
