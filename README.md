# Interview Coach Crew

Welcome to the Interview Coach Crew project, powered by [crewAI](https://crewai.com). This AI-powered interview coaching system helps candidates prepare for job interviews by conducting mock interviews and providing detailed performance evaluations.

## Features

- 🎯 **AI-Powered Mock Interviews**: Conducts realistic interview sessions based on resume and job description.
- 📄 **PDF Resume Support**: Automatically processes PDF resumes using RAG (Retrieval-Augmented Generation).
- 🔍 **Smart Context Retrieval**: Efficiently retrieves relevant resume information without overwhelming LLM context.
- 🚀 **Parallel Question Generation**: Generates a full set of curated questions in parallel for efficiency.
- 🌐 **FastAPI Backend**: Robust API for session management and interview orchestration.
- 🔄 **Flow-Based Architecture**: Uses CrewAI Flow for orchestrating multi-agent workflows.

## Architecture

The system is built on a **CrewAI Flow** (`GenerateInterviewQuestionsFlow`) that orchestrates the interview preparation process:

1.  **Preprocessing**: The job description is cleaned and focused on technical requirements using an LLM.
2.  **RAG Ingestion**: The candidate's resume (PDF) is ingested into a vector database (ChromaDB) using Google Gemini embeddings.
3.  **Roadmap Generation**: A `SupervisorCrew` analyzes the job description to identify key interview topics.
4.  **Contextual Retrieval**: For each topic, the RAG system retrieves relevant experience from the candidate's resume.
5.  **Parallel Question Generation**: An `InterviewCrew` generates tailored interview questions for each topic in parallel, ensuring a comprehensive and personalized interview experience.

## API Capabilities

The project provides a FastAPI-based backend with the following capabilities:

- **Session Management**: Start new interview sessions with resume uploads and job descriptions (`POST /api/v1/sessions`).
- **Question Retrieval**: Access pre-generated, curated questions tailored to the candidate.
- **Response Submission**: Submit candidate responses for the entire interview in a single batch (`POST /api/v1/sessions/{session_id}/responses`).
- **Transcript Access**: Retrieve full transcripts of the interview session (`GET /api/v1/sessions/{session_id}/transcript`).
- **Status Tracking**: Monitor the progress of the interview and evaluation.

> ⚠️ **Note**: The **Evaluation feature** is currently under development and is not yet ready for production use.

## RAG System

This project includes a sophisticated RAG system for handling large PDF resumes using **Google Gemini embeddings**.

- **Ingestion**: PDF resumes are chunked and embedded using Google's Gemini models.
- **Storage**: Embeddings are stored in a local **ChromaDB** vector store.
- **Retrieval**: During the interview generation, relevant resume sections are retrieved based on the specific interview topic, ensuring the LLM has the right context without exceeding token limits.

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management.

1. Install uv:
```bash
pip install uv
```

2. Install dependencies:
```bash
uv sync
```

3. Set up your environment:
Create a `.env` file and add your `GOOGLE_API_KEY`.

## Running the Project

### Starting the API Server

To start the FastAPI server:

```bash
uv run serve
```

The API will be available at `http://localhost:8000`. You can access the interactive documentation at `http://localhost:8000/docs`.

---

## Understanding The Crews

The system utilizes specialized crews to handle different stages of the interview process:

### Supervisor Crew
- **Supervisor Agent**: Analyzes the job description to identify key technical and behavioral topics, creating a structured interview roadmap.

### Interview Crew
- **Interviewer Agent**: Generates tailored, contextual interview questions for specific topics, leveraging retrieved information from the candidate's resume.

### Evaluation Crew
- **Evaluator Agent**: (In Development) Analyzes the interview transcript to provide feedback and performance scoring.

These crews collaborate within the `GenerateInterviewQuestionsFlow`, which manages the state and execution order of the interview preparation.

## Project Structure

```
interview_coach/
├── src/
│   ├── interview_coach/
│   │   ├── api/                  # FastAPI backend
│   │   ├── crews/                # CrewAI agent definitions
│   │   ├── questions_flow.py     # Main interview flow
│   │   └── main.py               # CLI entry point
│   ├── rag/                      # RAG system core
│   └── tools/                    # Custom tools
├── chroma_db/                    # Vector database storage
└── uploads/                      # Uploaded resumes
```

## Support

For support, questions, or feedback:

- Visit [crewAI documentation](https://docs.crewai.com)
- Reach out through [crewAI GitHub](https://github.com/joaomdmoura/crewai)
- [Join crewAI Discord](https://discord.com/invite/X4JWnZnxPb)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project uses crewAI and is subject to its licensing terms.

---

Let's create amazing interview preparation experiences with the power of AI and crewAI! 🚀
