# Interview Coach Crew

Welcome to the Interview Coach Crew project, powered by [crewAI](https://crewai.com). This AI-powered interview coaching system helps candidates prepare for job interviews by conducting mock interviews and providing detailed performance evaluations.

## Features

- 🎯 **AI-Powered Mock Interviews**: Conducts realistic interview sessions based on resume and job description
- 📊 **Performance Evaluation**: Provides comprehensive feedback and scoring
- 📄 **PDF Resume Support**: Automatically processes PDF resumes using RAG (Retrieval-Augmented Generation)
- 🔍 **Smart Context Retrieval**: Efficiently retrieves relevant resume information without overwhelming LLM context
- 💾 **Session Management**: Saves interview transcripts and evaluation reports
- 🔄 **Flow-Based Architecture**: Uses CrewAI Flow for orchestrating multi-agent workflows

## RAG System

This project includes a sophisticated RAG system for handling large PDF resumes using **Google Gemini embeddings**. See [RAG_ARCHITECTURE.md](RAG_ARCHITECTURE.md) for detailed documentation on:
- How RAG works in this application
- PDF ingestion and vector storage using ChromaDB
- Google Gemini embeddings integration
- Resume retrieval during interviews
- Testing and configuration options

## Installation

Ensure you have Python >=3.10 <3.14 installed on your system. This project uses [UV](https://docs.astral.sh/uv/) for dependency management and package handling, offering a seamless setup and execution experience.

First, if you haven't already, install uv:

```bash
pip install uv
```

Next, navigate to your project directory and install the dependencies:

(Optional) Lock the dependencies and install them by using the CLI command:
```bash
crewai install
```

### Customizing

**Add your `GOOGLE_API_KEY` into the `.env` file**

- Modify `src/interview_coach/config/agents.yaml` to define your agents
- Modify `src/interview_coach/config/tasks.yaml` to define your tasks
- Modify `src/interview_coach/crew.py` to add your own logic, tools and specific args
- Modify `src/interview_coach/main.py` to add custom inputs for your agents and tasks
- Modify `src/interview_coach/rag_config.py` to customize RAG parameters

## Running the Project

### Basic Usage (Demo Mode)

To run with demo data:

```bash
crewai run
```

### Running with PDF Resume

To run an interview with a PDF resume:

```bash
python -m interview_coach.main run_with_trigger '{
  "resume_pdf_path": "/path/to/resume.pdf",
  "job_description": "Your job description here...",
  "candidate_name": "Candidate Name:

- Visit [crewAI documentation](https://docs.crewai.com)
- Check [RAG_README.md](RAG_README.md) for RAG-specific questions
- Review [examples_rag.py](examples_rag.py) for usage examples
- Reach out through [crewAI GitHub](https://github.com/joaomdmoura/crewai)
- [Join crewAI Discord](https://discord.com/invite/X4JWnZnxPb)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project uses crewAI and is subject to its licensing terms.

---

Let's create amazing interview preparation experiences with the power of AI and crewAI! 🚀
```bash
python -m interview_coach.main run_with_trigger '{
  "resume": "Your resume text here...",
  "job_description": "Your job description here...",
  "candidate_name": "Candidate Name"
}'
```

### Testing RAG System

Test the RAG system independently:

```bash
# Test with a PDF
python src/interview_coach/rag_utils.py test /path/to/resume.pdf

# List stored sessions
python src/interview_coach/rag_utils.py list

# Clear all sessions
python src/interview_coach/rag_utils.py clear
```

### Running Examples

See various usage examples:

```bash
# Run example 2 (test RAG independently)
python examples_rag.py 2

# Run example 4 (text resume without RAG)
python examples_rag.py 4
```

## Understanding Your Crew

The Interview Coach Crew is composed of multiple AI agents working together:

### Interview Crew
- **Interviewer Agent**: Conducts the mock interview based on resume and job description
- **Question Generator**: Creates relevant interview questions

### Evaluation Crew
- **Evaluator Agent**: Analyzes interview performance
- **Scoring Agent**: Provides detailed scores and feedback

These agents collaborate through tasks defined in `config/tasks.yaml`, leveraging the RAG system to efficiently access resume information.

## Project Structure

```
interview_coach/
├── src/interview_coach/
│   ├── main.py                    # Main flow orchestration
│   ├── rag_service.py            # RAG system core
│   ├── rag_utils.py              # RAG utilities
│   ├── crews/
│   │   ├── interview_crew/       # Interview conducting agents
│   │   └── evaluation_crew/      # Performance evaluation agents
│   └── tools/
│       ├── resume_retrieval_tool.py  # RAG retrieval tool
│       └── custom_tool.py
├── RAG_README.md                 # Detailed RAG documentation
├── examples_rag.py              # RAG usage examples
├── chroma_db/                   # Vector database storage
└── interview_results/           # Saved interview sessions
```

## Output

After running an interview, results are saved in `interview_results/<session_id>/`:
- `interview_transcript.txt` - Complete interview conversation
- `evaluation_report.txt` - Performance analysis and feedback
- `session_metadata.json` - Session information including RAG stats

## Support

For support, questions, or feedback:

- Visit [crewAI documentation](https://docs.crewai.com)
- Check [RAG_ARCHITECTURE.md](RAG_ARCHITECTURE.md) for RAG-specific questions
- Review [examples_rag.py](examples_rag.py) for usage examples
- Reach out through [crewAI GitHub](https://github.com/joaomdmoura/crewai)
- [Join crewAI Discord](https://discord.com/invite/X4JWnZnxPb)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project uses crewAI and is subject to its licensing terms.

---

Let's create amazing interview preparation experiences with the power of AI and crewAI! 🚀
