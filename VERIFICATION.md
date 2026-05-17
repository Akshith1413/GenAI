# Verification Guide: Agentic Document Review System

This document maps PRD requirements to verifiable tests.

## PRD Requirement → Implementation Mapping

### 1. Core Workflow (The "Loop")

| PRD Requirement | Implementation | Test Command |
|-----------------|----------------|--------------|
| Input: User uploads messy notes | `POST /documents` with `content` field | ```powershell
$body = @{
    content = "Meeting today. John said we need to fix the bug. Sarah will test. Budget approved for Q2."
    document_type = "meeting_minutes"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/documents" -Method POST -ContentType "application/json" -Body $body
``` |
| Drafting: Writer Agent generates Markdown | `agents.py` - `writer_agent()` function | Check response for `document_id` |
| Review: Critic Agent compares against rubric | `agents.py` - `critic_agent()` function | Check status endpoint for critique JSON |
| Logic Gate: If errors → loop back | `workflow.py` - `decision_node()` & `should_continue()` | Verify revision_count increments |
| If passed → Human-in-the-Loop | `workflow.py` - `human_review` node | Status becomes `awaiting_approval` |
| Output: Finalized document | `GET /documents/{id}/final` | Returns approved markdown |

### 2. Technical Specifications

| PRD Requirement | Implementation | Verification |
|-----------------|----------------|--------------|
| **Orchestration: LangGraph** | `workflow.py` - `StateGraph` with cyclic edges | Check file uses `StateGraph`, `add_conditional_edges` |
| **Backend: FastAPI** | `main.py` - FastAPI app with endpoints | `GET /health` returns 200 |
| **LLMs: Groq** | `agents.py` - `groq_client` with specified models | Models: `llama-3.3-70b-versatile` (Writer & Critic) |
| **Data Format: JSON internal** | `models.py` - `CriticFeedback` Pydantic model | Critique output is valid JSON with score/passed/missing_elements/improvement_suggestions |
| **Data Format: Markdown output** | Writer agent returns markdown | Check `/documents/{id}/draft` returns markdown content |

### 3. Functional Requirements

#### 3.1 State Management - `revision_count` prevents infinite loops

**Test:**
```powershell
# Create document with low max_revisions
$body = @{
    content = "Poor quality notes with missing info"
    document_type = "meeting_minutes"
    max_revisions = 1
} | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8000/documents" -Method POST -ContentType "application/json" -Body $body

# Check status - should show revision_count <= max_revisions
Invoke-RestMethod -Uri "http://localhost:8000/documents/$($response.document_id)" | Select-Object revision_count, max_revisions, status
```

**Expected:** `revision_count` ≤ `max_revisions`, status is `max_revisions_reached` or `awaiting_approval`

**Code Location:** `workflow.py:74-77` - `decision_node()` checks `revision_count >= max_revisions`

---

#### 3.2 Structured Critique - JSON with specific fields

**Test:**
```powershell
# Create document and check critique format
$body = @{
    content = "Meeting on May 2. Attendees: John, Sarah. Discussed Q2 budget."
    document_type = "meeting_minutes"
} | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8000/documents" -Method POST -ContentType "application/json" -Body $body

# Get status and check critique structure
$status = Invoke-RestMethod -Uri "http://localhost:8000/documents/$($response.document_id)"
$status.critique
```

**Expected Output Format:**
```json
{
  "score": 85,
  "passed": false,
  "missing_elements": ["Meeting start time", "Action items with owners"],
  "improvement_suggestions": ["Add meeting time", "Add action items section"]
}
```

**Code Location:** `models.py:7-12` - `CriticFeedback` Pydantic model

---

#### 3.3 HITL - API exposes endpoint to "resume" after human review

**Test:**
```powershell
# 1. Create document
$body = @{
    content = "Good meeting notes with all details. Date: May 2, 2026. Time: 2pm. Attendees: John, Sarah, Mike. Discussed Q2 budget of $50K. Action: John to prepare report by Friday May 9."
    document_type = "meeting_minutes"
    max_revisions = 3
} | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://localhost:8000/documents" -Method POST -ContentType "application/json" -Body $body
$docId = $response.document_id

# 2. Check status until awaiting_approval (may need to poll)
Start-Sleep -Seconds 5
$status = Invoke-RestMethod -Uri "http://localhost:8000/documents/$docId"
Write-Output "Status: $($status.status)"

# 3. Submit human review - APPROVE
$review = @{
    document_id = $docId
    decision = "approve"
    feedback = "Looks good!"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/documents/$docId/review" -Method POST -ContentType "application/json" -Body $review

# 4. Verify approved
$final = Invoke-RestMethod -Uri "http://localhost:8000/documents/$docId"
Write-Output "Final status: $($final.status)"

# 5. Get final document
Invoke-RestMethod -Uri "http://localhost:8000/documents/$docId/final"
```

**Expected:** After `approve`, status becomes `approved` and `/final` endpoint returns document

**Code Location:** `main.py:78-108` - `submit_review()` endpoint, `resume_document()` in workflow

---

## End-to-End Test Script

```powershell
# ============================================
# COMPLETE VERIFICATION TEST
# ============================================

$baseUrl = "http://localhost:8000"

# 1. Health Check
Write-Host "`n=== TEST 1: Health Check ===" -ForegroundColor Green
$health = Invoke-RestMethod -Uri "$baseUrl/health"
Write-Output $health

# 2. Create Document
Write-Host "`n=== TEST 2: Create Document ===" -ForegroundColor Green
$body = @{
    content = @"
Meeting Notes - May 2, 2026
Project Alpha Review

Attendees: 
- John Smith (PM)
- Sarah Chen (Dev)  
- Mike Johnson (QA)

Discussion:
- Q2 budget approved at $50,000
- Timeline moved up by 2 weeks
- New feature requests from client

Action Items:
- John: Update project plan by Friday
- Sarah: Start backend refactoring Monday
- Mike: Prepare test cases by Wednesday

Next Meeting: May 9, 2026 at 2pm
"@
    document_type = "meeting_minutes"
    max_revisions = 3
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$baseUrl/documents" -Method POST -ContentType "application/json" -Body $body
$docId = $response.document_id
Write-Output "Document ID: $docId"
Write-Output "Initial Status: $($response.status)"

# 3. Poll for Status (wait for workflow to complete)
Write-Host "`n=== TEST 3: Poll for Status ===" -ForegroundColor Green
$maxAttempts = 10
for ($i = 0; $i -lt $maxAttempts; $i++) {
    Start-Sleep -Seconds 3
    $status = Invoke-RestMethod -Uri "$baseUrl/documents/$docId"
    Write-Output "Attempt $($i+1): Status=$($status.status), Revisions=$($status.revision_count)"
    
    if ($status.status -eq "awaiting_approval" -or $status.status -eq "max_revisions_reached") {
        break
    }
}

# 4. Check Draft Content
Write-Host "`n=== TEST 4: Check Draft ===" -ForegroundColor Green
$draft = Invoke-RestMethod -Uri "$baseUrl/documents/$docId/draft"
Write-Output "Draft Content Preview:"
Write-Output $draft.content.Substring(0, [Math]::Min(200, $draft.content.Length))
Write-Output "..."

# 5. Check Critique Structure
Write-Host "`n=== TEST 5: Critique Structure ===" -ForegroundColor Green
$fullStatus = Invoke-RestMethod -Uri "$baseUrl/documents/$docId"
if ($fullStatus.critique) {
    Write-Output "Score: $($fullStatus.critique.score)"
    Write-Output "Passed: $($fullStatus.critique.passed)"
    Write-Output "Missing Elements: $($fullStatus.critique.missing_elements -join ', ')"
    Write-Output "Suggestions: $($fullStatus.critique.improvement_suggestions -join ', ')"
}

# 6. Human Review - Approve
Write-Host "`n=== TEST 6: Human Review (Approve) ===" -ForegroundColor Green
$review = @{
    document_id = $docId
    decision = "approve"
    feedback = "Document looks professional and complete."
} | ConvertTo-Json

$reviewResult = Invoke-RestMethod -Uri "$baseUrl/documents/$docId/review" -Method POST -ContentType "application/json" -Body $review
Write-Output "Review submitted. New status: $($reviewResult.new_status)"

# 7. Get Final Document
Write-Host "`n=== TEST 7: Final Document ===" -ForegroundColor Green
$final = Invoke-RestMethod -Uri "$baseUrl/documents/$docId/final"
Write-Output "Final Status: $($final.status)"
Write-Output "Revision Count: $($final.revision_count)"
Write-Output "Completed At: $($final.completed_at)"
Write-Output "`nFinal Content:"
Write-Output $final.final_content

# 8. List Active Documents
Write-Host "`n=== TEST 8: List Active Documents ===" -ForegroundColor Green
$active = Invoke-RestMethod -Uri "$baseUrl/active-documents"
Write-Output "Active documents: $($active.count)"

Write-Host "`n=== ALL TESTS COMPLETE ===" -ForegroundColor Green
```

---

## Manual Verification Checklist

- [ ] **Server starts without errors**: `python main.py` runs without import/connection errors
- [ ] **Health endpoint works**: `GET /health` returns 200 with service info
- [ ] **Document creation works**: `POST /documents` returns document_id
- [ ] **Writer generates markdown**: Draft content has proper headings, lists, formatting
- [ ] **Critic produces valid JSON**: Critique has all 4 required fields (score, passed, missing_elements, improvement_suggestions)
- [ ] **Loop works**: If critique fails, system revises (revision_count > 1)
- [ ] **Max revisions prevents infinite loops**: Setting max_revisions=1 stops at 1 revision
- [ ] **HITL pause works**: Approved documents reach `awaiting_approval` status
- [ ] **Resume works**: `POST /{id}/review` with `approve` changes status to `approved`
- [ ] **Final output works**: `GET /{id}/final` returns completed document
- [ ] **Swagger UI works**: `http://localhost:8000/docs` shows all endpoints

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "GROQ_API_KEY not found" | .env not loaded | Verify `load_dotenv()` in `agents.py` line 10 |
| "Revision count exceeds max" | Logic error | Check `workflow.py` line 74-77 |
| Critique missing fields | Pydantic validation | Check `models.py` `CriticFeedback` model |
| HITL not pausing | Status not set | Check `decision_node()` sets `awaiting_approval` |
