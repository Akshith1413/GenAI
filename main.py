"""FastAPI application for the Agentic Document Review System."""

import os
from datetime import datetime
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from models import DocumentInput, HumanReviewDecision, DocumentOutput, DocumentState
from workflow import DocumentWorkflow
from file_parser import validate_and_extract_text

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Agentic Document Review System",
    description="Multi-agent system for automated document drafting and verification",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for UI
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")

# Initialize workflow manager
workflow_manager = DocumentWorkflow()


@app.post("/documents/upload", response_model=Dict[str, Any])
async def upload_document(
    file: UploadFile = File(..., description=".docx file to process"),
    document_type: str = Form("meeting_minutes", description="Type of document: meeting_minutes, report, memo, proposal"),
    max_revisions: int = Form(3, ge=1, le=5, description="Maximum revision cycles")
):
    """
    Upload a .docx file and start document drafting workflow.
    
    - Extracts text from Word document
    - Initiates the Writer → Critic → (loop or HITL) workflow
    - Returns document ID for tracking
    
    **Note:** Currently only .docx format is supported.
    """
    try:
        # Validate and extract text from file
        extracted_text, filename = await validate_and_extract_text(file)
        
        # Create document input
        input_data = DocumentInput(
            content=extracted_text,
            document_type=document_type,
            max_revisions=max_revisions
        )
        
        # Start workflow
        document_id = workflow_manager.start_document(input_data)
        status = workflow_manager.get_status(document_id)
        
        return {
            "document_id": document_id,
            "filename": filename,
            "extracted_length": len(extracted_text),
            "status": status.get("status"),
            "revision_count": status.get("revision_count"),
            "message": "Document uploaded and workflow started successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded file: {str(e)}")


@app.post("/documents", response_model=Dict[str, Any])
async def create_document(input_data: DocumentInput):
    """
    Start a new document drafting workflow.
    
    - Takes raw notes/transcripts as input
    - Initiates the Writer → Critic → (loop or HITL) workflow
    - Returns document ID for tracking
    """
    try:
        document_id = workflow_manager.start_document(input_data)
        
        # Get initial status
        status = workflow_manager.get_status(document_id)
        
        return {
            "document_id": document_id,
            "status": status.get("status"),
            "revision_count": status.get("revision_count"),
            "message": "Document workflow started successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start document workflow: {str(e)}")


@app.get("/documents/{document_id}", response_model=Dict[str, Any])
async def get_document_status(document_id: str):
    """
    Get the current status of a document workflow.
    
    - Shows current draft, critique, revision count, and status
    """
    try:
        status = workflow_manager.get_status(document_id)
        return {
            "document_id": document_id,
            "status": status.get("status"),
            "revision_count": status.get("revision_count"),
            "max_revisions": status.get("max_revisions"),
            "document_type": status.get("document_type"),
            "raw_input": status.get("raw_input"),
            "current_draft": status.get("current_draft"),
            "critique": status.get("critique")
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve status: {str(e)}")


@app.get("/documents/{document_id}/draft", response_model=Dict[str, str])
async def get_document_draft(document_id: str):
    """Get the current draft content of a document."""
    try:
        status = workflow_manager.get_status(document_id)
        draft = status.get("current_draft")
        
        if not draft:
            raise HTTPException(status_code=404, detail="No draft available yet")
        
        return {
            "document_id": document_id,
            "content": draft,
            "status": status.get("status")
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/documents/{document_id}/review")
async def submit_review(document_id: str, decision: HumanReviewDecision):
    """
    Submit human review decision for a document awaiting approval.
    
    - **approve**: Finalizes the document
    - **reject**: Discards the document
    - **request_changes**: Sends back to Writer with feedback for revision
    """
    try:
        if decision.document_id != document_id:
            raise HTTPException(status_code=400, detail="Document ID mismatch")
        
        result = workflow_manager.resume_document(
            document_id=document_id,
            decision=decision.decision,
            feedback=decision.feedback
        )
        
        return {
            "document_id": document_id,
            "decision": decision.decision,
            "new_status": result.get("status"),
            "revision_count": result.get("revision_count"),
            "message": f"Document {decision.decision}d successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process review: {str(e)}")


@app.get("/documents/{document_id}/final", response_model=DocumentOutput)
async def get_final_document(document_id: str):
    """
    Get the finalized document output.
    
    - Only available for approved documents
    """
    try:
        status = workflow_manager.get_status(document_id)
        doc_state = DocumentState(**status)
        
        if doc_state.status != "approved":
            raise HTTPException(
                status_code=400, 
                detail=f"Document is not approved. Current status: {doc_state.status}"
            )
        
        return DocumentOutput(
            document_id=document_id,
            final_content=doc_state.current_draft or "",
            revision_count=doc_state.revision_count,
            status=doc_state.status,
            created_at=doc_state.created_at,
            completed_at=doc_state.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/active-documents")
async def list_active_documents():
    """List all active document sessions."""
    sessions = []
    for doc_id, state in workflow_manager.active_sessions.items():
        sessions.append({
            "document_id": doc_id,
            "status": state.get("status"),
            "revision_count": state.get("revision_count"),
            "created_at": state.get("created_at")
        })
    
    return {"documents": sessions, "count": len(sessions)}


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document session."""
    if document_id in workflow_manager.active_sessions:
        del workflow_manager.active_sessions[document_id]
        return {"message": f"Document {document_id} deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Document not found")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Agentic Document Review System",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
