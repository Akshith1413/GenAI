from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class CriticFeedback(BaseModel):
    """Structured critique output from the Critic agent."""
    score: int = Field(..., ge=0, le=100, description="Quality score 0-100")
    passed: bool = Field(..., description="Whether the document meets all requirements")
    missing_elements: List[str] = Field(default_factory=list, description="List of missing or incorrect elements")
    improvement_suggestions: List[str] = Field(default_factory=list, description="Specific suggestions for improvement")


class DocumentState(BaseModel):
    """State management for the document review workflow."""
    document_id: str = Field(..., description="Unique identifier for the document")
    document_type: Literal["meeting_minutes", "report", "memo", "proposal", "prd"] = Field(
        default="meeting_minutes", description="Type of document being created"
    )
    raw_input: str = Field(..., description="Original messy input from user")
    current_draft: Optional[str] = Field(default=None, description="Current markdown draft")
    revision_count: int = Field(default=0, description="Number of revision cycles completed")
    max_revisions: int = Field(default=3, description="Maximum allowed revisions to prevent infinite loops")
    critique: Optional[CriticFeedback] = Field(default=None, description="Latest critique from Critic agent")
    status: Literal["drafting", "reviewing", "awaiting_approval", "approved", "rejected", "max_revisions_reached"] = Field(
        default="drafting", description="Current status in the workflow"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentInput(BaseModel):
    """Input model for document creation."""
    content: str = Field(..., min_length=10, description="Raw notes or meeting transcript")
    document_type: Literal["meeting_minutes", "report", "memo", "proposal", "prd"] = Field(
        default="meeting_minutes", description="Type of document to generate"
    )
    max_revisions: int = Field(default=3, ge=1, le=5, description="Maximum revision cycles")


class HumanReviewDecision(BaseModel):
    """Human-in-the-loop review decision."""
    document_id: str = Field(..., description="Document ID to review")
    decision: Literal["approve", "reject", "request_changes"] = Field(..., description="Human decision")
    feedback: Optional[str] = Field(default=None, description="Optional human feedback")


class DocumentOutput(BaseModel):
    """Output model for completed documents."""
    document_id: str
    final_content: str
    revision_count: int
    status: str
    created_at: datetime
    completed_at: datetime
