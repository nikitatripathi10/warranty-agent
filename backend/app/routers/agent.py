"""
Chat-style warranty agent endpoint.

POST /agent/query
  Accepts a user_id and a natural-language question.
  Returns an LLM-generated answer grounded in the user's purchase records.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AgentQueryRequest, AgentQueryResponse
from app.services.warranty_agent import answer_query

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/query",
    response_model=AgentQueryResponse,
    summary="Ask the warranty agent a question about your purchases",
)
def agent_query(
    body: AgentQueryRequest,
    db: Session = Depends(get_db),
) -> AgentQueryResponse:
    """
    Send a natural-language question to the Warranty Radar AI agent.
    The agent answers based on the user's actual purchase records from the database.

    Examples:
      - "When does my laptop warranty expire?"
      - "Which of my products can still be returned?"
      - "Do I have any products with low-confidence warranty data?"
      - "Mera Sony headphone kab tak warranty mein hai?"
    """
    logger.info(
        "Agent query for user %s: %r",
        body.user_id,
        body.question[:60],
    )
    answer = answer_query(db, body.user_id, body.question)
    return AgentQueryResponse(answer=answer, user_id=body.user_id)
