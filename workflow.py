"""LangGraph workflow for the Agentic Document Review System."""

import uuid
from datetime import datetime
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from models import DocumentState, CriticFeedback, DocumentInput
from agents import writer_agent, critic_agent


def create_document_state(input_data: DocumentInput) -> DocumentState:
    """Initialize a new document state."""
    return DocumentState(
        document_id=str(uuid.uuid4()),
        raw_input=input_data.content,
        document_type=input_data.document_type,
        max_revisions=input_data.max_revisions,
        status="drafting"
    )


def writer_node(state: Dict[str, Any], document_type: str) -> Dict[str, Any]:
    """Writer node: Generates or revises the document."""
    doc_state = DocumentState(**state)
    
    # Generate draft
    draft = writer_agent(doc_state, document_type)
    
    # Update state
    doc_state.current_draft = draft
    doc_state.revision_count += 1
    doc_state.status = "reviewing"
    doc_state.updated_at = datetime.utcnow()
    
    return doc_state.model_dump()


def critic_node(state: Dict[str, Any], document_type: str) -> Dict[str, Any]:
    """Critic node: Evaluates the document quality."""
    doc_state = DocumentState(**state)
    
    if not doc_state.current_draft:
        raise ValueError("No draft available for critique")
    
    # Get critique
    critique = critic_agent(
        document=doc_state.current_draft,
        source_input=doc_state.raw_input,
        document_type=document_type
    )
    
    doc_state.critique = critique
    doc_state.updated_at = datetime.utcnow()
    
    return doc_state.model_dump()


def decision_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Logic gate: Determine next step based on critique and revision count."""
    doc_state = DocumentState(**state)
    
    # Check if max revisions reached
    if doc_state.revision_count >= doc_state.max_revisions:
        doc_state.status = "max_revisions_reached"
        doc_state.updated_at = datetime.utcnow()
        return doc_state.model_dump()
    
    # Check if critique passed
    if doc_state.critique and doc_state.critique.passed and doc_state.critique.score >= 90:
        doc_state.status = "awaiting_approval"
        doc_state.updated_at = datetime.utcnow()
    
    return doc_state.model_dump()


def should_continue(state: Dict[str, Any]) -> Literal["writer", "human_review", "max_revisions"]:
    """Conditional edge: Determine workflow path."""
    doc_state = DocumentState(**state)
    
    if doc_state.status == "max_revisions_reached":
        return "max_revisions"
    
    if doc_state.status == "awaiting_approval":
        return "human_review"
    
    # Otherwise, loop back to writer for revision
    return "writer"


class DocumentWorkflow:
    """Manages the document review workflow graph."""
    
    def __init__(self):
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def _build_graph(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("writer", lambda state: writer_node(state, self._get_doc_type(state)))
        workflow.add_node("critic", lambda state: critic_node(state, self._get_doc_type(state)))
        workflow.add_node("decision", decision_node)
        workflow.add_node("human_review", self._human_review_node)
        workflow.add_node("max_revisions", self._max_revisions_node)
        
        # Add edges
        workflow.set_entry_point("writer")
        workflow.add_edge("writer", "critic")
        workflow.add_edge("critic", "decision")
        
        # Conditional edges from decision
        workflow.add_conditional_edges(
            "decision",
            should_continue,
            {
                "writer": "writer",
                "human_review": "human_review",
                "max_revisions": "max_revisions"
            }
        )
        
        workflow.add_edge("human_review", END)
        workflow.add_edge("max_revisions", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _get_doc_type(self, state: Dict[str, Any]) -> str:
        """Extract document type from state."""
        return state.get("document_type", "meeting_minutes")
    
    def _human_review_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Pause for human review - stores state for later resume."""
        doc_state = DocumentState(**state)
        self.active_sessions[doc_state.document_id] = state
        return state
    
    def _max_revisions_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle max revisions reached."""
        doc_state = DocumentState(**state)
        self.active_sessions[doc_state.document_id] = state
        return state
    
    def start_document(self, input_data: DocumentInput) -> str:
        """Start a new document workflow."""
        doc_state = create_document_state(input_data)
        doc_state.document_type = input_data.document_type  # Store type in state
        
        initial_state = doc_state.model_dump()
        initial_state["document_type"] = input_data.document_type
        
        # Run the graph
        thread_id = doc_state.document_id
        config = {"configurable": {"thread_id": thread_id}}
        
        result = self.graph.invoke(initial_state, config)
        
        # Store for potential resume
        self.active_sessions[thread_id] = result
        
        return thread_id
    
    def resume_document(self, document_id: str, decision: str, feedback: str = None) -> Dict[str, Any]:
        """Resume workflow after human review."""
        if document_id not in self.active_sessions:
            raise ValueError(f"Document session {document_id} not found")
        
        state = self.active_sessions[document_id]
        doc_state = DocumentState(**state)
        
        if decision == "approve":
            doc_state.status = "approved"
        elif decision == "reject":
            doc_state.status = "rejected"
        elif decision == "request_changes":
            doc_state.status = "drafting"
            # Add human feedback to critique for next revision
            if doc_state.critique:
                doc_state.critique.passed = False
                doc_state.critique.score = max(50, doc_state.critique.score - 10)
                if feedback:
                    doc_state.critique.improvement_suggestions.append(f"Human feedback: {feedback}")
            doc_state.updated_at = datetime.utcnow()
            
            # Re-run the graph
            config = {"configurable": {"thread_id": document_id}}
            result = self.graph.invoke(doc_state.model_dump(), config)
            self.active_sessions[document_id] = result
            return result
        
        doc_state.updated_at = datetime.utcnow()
        final_state = doc_state.model_dump()
        self.active_sessions[document_id] = final_state
        
        return final_state
    
    def get_status(self, document_id: str) -> Dict[str, Any]:
        """Get current status of a document workflow."""
        if document_id not in self.active_sessions:
            raise ValueError(f"Document session {document_id} not found")
        return self.active_sessions[document_id]
