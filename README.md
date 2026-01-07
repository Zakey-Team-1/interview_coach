# Interview Coach

Welcome to the **Interview Coach**, an advanced AI-powered interview coaching system built with [crewAI](https://crewai.com). This system automates the end-to-end mock interview process—from analyzing job descriptions (JD) and resumes to generating tailored questions and producing comprehensive performance reports.

## Features

* **AI-Powered Mock Interviews**: Generates realistic, high-signal questions by cross-referencing resumes with specific JD requirements.
* **RAG-Enhanced Context**: Ingests PDF resumes into a RAG system to ensure questions are grounded in the candidate's actual experience.
* **Parallel Processing**: Uses parallel agent execution to clean JDs and generate questions simultaneously, reducing latency.
* **Comprehensive Evaluation**: A dedicated crew of agents evaluates responses to produce a detailed report covering strengths, weaknesses, and actionable advice.
* **Stateless & Scalable**: A FastAPI backend designed for Cloud Run, utilizing Supabase for persistent data storage.

## Architecture

The system is orchestrated using **CrewAI Flows**, following a structured 5-step pipeline:

1. **Preprocessing & Ingestion**: In parallel, the system cleans/preprocesses the Job Description and ingests the Resume PDF into the RAG vector store.
2. **Topic Identification**: A **Supervisor Agent** analyzes the cleaned JD to identify 5-7 core topics/skill sets required for the role.
3. **Parallel Question Generation**: Each topic is passed to a **Question Generation Agent** in parallel. This agent uses relevant snippets from the Resume (via RAG) to create tailored, technical interview questions.
4. **Frontend Delivery**: The curated list of questions is dispatched to the Google AI Studio-based frontend.
5. **Evaluation Flow**: Once the user submits their answers, a **Crew of Agents** evaluates the responses against the JD to produce a final report including a summary, main strengths, weaknesses, and coaching advice.

## Tech Stack

* **Framework**: [crewAI](https://crewai.com) (Agent Orchestration & Flows)
* **Backend**: FastAPI (Python)
* **Frontend**: Google AI Studio
* **Database**: Supabase (Postgres)
* **Embeddings**: Google Gemini Embeddings 001
* **Deployment**: Google Cloud Run (CI/CD via GCP)

## Observability & Monitoring

To ensure the reliability of the multi-agent orchestration and to monitor LLM costs and latency, this project integrates LangFuse.

* Detailed Tracing: Every step of the CrewAI Flow is traced.
* Performance Metrics: Track the latency of parallel agent execution and token usage for Google Gemini models.

## 📡 API & Infrastructure

### Stateless Backend

The FastAPI backend is entirely **stateless**. It receives data via API calls, processes it through the CrewAI agents, and returns the response. This allows for seamless scaling on Google Cloud Run.

### Deployment (CI/CD)

The project is deployed directly to **Google Cloud Run** from the GitHub repository.

* **Pipeline**: A CI/CD pipeline is triggered on every commit to the `master` branch.
* **Infrastructure**: Managed via Artifact Registry and Cloud Run for high availability.

## 📂 Project Structure

```text
interview_coach/
├── src/
│   ├── interview_coach/
│   │   ├── api/                 # Stateless FastAPI backend
│   │   ├── crews/               # CrewAI agent & task definitions
│   │   │   ├── supervisor/      # JD analysis crew
│   │   │   ├── interview/       # Question generation crew
│   │   │   └── evaluation/      # Response evaluation crew
│   │   ├── questions_flow.py    # Main orchestration flow
│   │   └── main.py              # Entry point
│   ├── rag/                     # RAG system logic
│   └── tools/                   # Custom tools for agents

```

## ⚙️ Installation & Setup

Ensure you have Python `>=3.10 <3.14` and [UV](https://docs.astral.sh/uv/) installed.

1. **Clone and Install**:

```bash
git clone [https://github.com/Zakey-Team-1/interview_coach]
cd interview_coach
uv tool install crewai
crewai install

```

2. **Environment Variables**:
Create a copy from the `.env.example` file named `.env` and fill it

3. **Run Locally**:

```bash
uv run serve

```

The API will be available at `http://localhost:8080`. Access the interactive docs at `/docs`.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests to improve the agent prompts or the orchestration flow.
