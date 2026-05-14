# 🤖 Agentic AI Document Review System

![Agentic Workflow](https://img.shields.io/badge/Architecture-Multi--Agent-blue) ![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python) ![FastAPI/Flask](https://img.shields.io/badge/Framework-Flask%2FFastAPI-green) ![Deployment](https://img.shields.io/badge/Deployment-Render-purple)

**Live Demo:** [https://genai-lpjy.onrender.com/](https://genai-lpjy.onrender.com/)

---

## 📖 Executive Problem Statement

In professional services (Law, Consulting, Product Management), professionals spend an exorbitant amount of time drafting, reviewing, and verifying massive documents such as Product Requirement Documents (PRDs), legal contracts, and compliance memos. Manual review is prone to human error, inconsistencies, and formatting deviations, causing severe operational bottlenecks.

The objective of this project is to build an **Agentic AI Document Workflow**. Using an autonomous multi-agent architecture, the system accepts a rough draft or bullet points, automatically generates a highly structured professional document (like a PRD), and utilizes a secondary "Reviewer AI" to critique and refine the document against predefined company standards.

---

## 🎯 Business Objectives and KPIs

The strategic goal is to **reduce document turnaround time from hours to minutes** while maintaining absolute structural consistency.

**Success Criteria:**
- The system consistently outputs valid, deeply structured Markdown or JSON documents.
- No required sections are dropped.
- Successful implementation of **"Agentic Routing"**—the ability of the AI to self-correct and loop back if the internal reviewer agent detects missing information.

---

## 👥 User Personas and Workflows

| Persona | Primary Needs | System Interaction and Workflow |
| :--- | :--- | :--- |
| **Product Manager / Consultant** | Rapid transformation of rough meeting notes into polished, actionable documents. | Inputs a raw text prompt or meeting transcript. The system outputs a fully structured PRD containing user stories, edge cases, and tech specs. |
| **Compliance/QA Reviewer** | Ensuring documents adhere strictly to company templates and lack material errors. | Acts as the "Human-in-the-loop," receiving flagged issues from the AI reviewer before giving final approval. |

---

## ⚙️ Minimum Viable Product (MVP) Specifications

The foundational feature of this project is the **Multi-Agent Orchestrator**. Instead of a single LLM call, the system utilizes distinct AI personas:
1. **Writer Agent:** Responsible for drafting the content based on user input.
2. **Critic Agent:** Responsible for evaluating the draft against a strict rubric.

**State Management & Cyclic Routing:** 
The system processes an input, generates a draft, and passes it to the Critic. If the Critic finds missing elements (e.g., "You forgot to include success metrics"), the Writer must automatically revise the document before presenting it to the user.

---

## 🏗️ Architectural Directives and Technology Stack

| Component | Technology | Architectural Rationale |
| :--- | :--- | :--- |
| **Backend / Web App** | Python, Flask/FastAPI | Required for exposing the complex agent workflows as consumable web interfaces and REST endpoints. |
| **Agent Framework** | LangGraph / Custom Graph | Provides robust state management and graph-based routing for multi-agent cyclic workflows. |
| **LLM Provider** | LLaMA / Groq / GPT | Excels exceptionally at long-form writing, coding, and document analysis tasks. |

---

## 👨‍💻 Team & Contributions

This project was developed collaboratively by a team of 4 engineers:

*   **Harsha:** 
    *   Created the foundational static configurations for the Critic and Writer agents.
*   **Akshith:** 
    *   Combined both agent models into a unified, dynamic workflow.
    *   Significantly improved the accuracy of the multi-agent routing.
    *   Built and deployed the dynamic web application (`Flask`).
    *   Transformed static JSON structures into dynamic parsing systems (e.g., dynamic score extraction).
    *   Deployed the final application to Render.
*   **Shivani:** 
    *   Implemented structured JSON output generation.
    *   Engineered the downloadable output file functionality.
*   **Kamlesh:** 
    *   Configured the LangGraph architecture.
    *   Developed the "Upload by Document" ingestion pipeline.

---

## 🚀 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone <repo_url>
   cd GenAI
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Environment Variables:**
   Create a `.env` file in the root directory and add your API keys:
   ```env
   GROQ_API_KEY=your_api_key_here
   ```

5. **Start the Web Application:**
   ```bash
   python app.py
   ```
   *Navigate to `http://127.0.0.1:5000` in your web browser.*

6. **Run via Terminal (CLI Mode):**
   ```bash
   python run.py
   ```
