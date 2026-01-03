#!/usr/bin/env python3
from pathlib import Path
import os
import sys

from interview_coach.main import InterviewCoachFlow


JOB_DESCRIPTION = """
At Phaedon

At Phaedon, we are revolutionizing how companies engage with their audiences and are passionate about sparking participation to drive growth for both our clients and our employees. Phaedon is a data-driven, tech-enabled marketing organization with a breadth of capabilities that go beyond our competitors and redefine traditional industry archetypes. We have a history of delivering game-changing results for notable brands across advanced analytics, loyalty technology and services, marketing communications, and experience transformation to bring intelligent imagination and solve our clients’ biggest business and brand challenges. And every role at Phaedon has an integral part to play in fulfilling this vision.

About the Role:

This is an excellent opportunity for an innovator and problem solver who thrives at the intersection of AI, cloud engineering, and product development. We are seeking an AI/ML Engineer to join our analytics and product development team. You will be a key member of our team, responsible for building, deploying, and scaling AI-powered data products and analytics solutions that solve real client challenges.

Essential Duties/Responsibilities:

Product Engineering & AI Implementation:

Design, build, and deploy AI-powered data products and analytics solutions using cutting-edge technologies
Implement and productionalize AI/ML models using AWS Bedrock and other AI services
Transform proof-of-concept work into robust, production-ready systems
Develop RAG (Retrieval-Augmented Generation) systems for AI applications
Build cloud-native applications with focus on scalability, reliability, and performance

Client Service & Analytics Delivery:

Work directly with clients to understand business requirements and translate them into product requirements and technical solutions
Present product requirements, user flows, and technical findings and recommendations to client stakeholders with clarity and professionalism
Conduct exploratory data analysis and deliver actionable insights through clear visualizations and reports
Collaborate with client teams to ensure successful implementation and adoption of analytics solutions

Cloud Infrastructure & Data Engineering:

Architect and maintain data lake solutions using AWS native tools including Lake Formation, Glue, and Athena
Develop automation and monitoring solutions using Lambda and other AWS services
Create and maintain Infrastructure-as-Code (IAC) using Terraform, Pulumi and CloudFormation
Build data pipelines that synthesize complex datasets from multiple sources into actionable insights

Quality & Production Focus:

Implement error-proofing strategies and robust testing frameworks including integration testing
Develop CI/CD pipelines for automated deployment and model versioning
Create monitoring and logging solutions for production AI systems
Ensure security best practices for AI applications and data handling

Location: Minneapolis (hybrid)

Basic Qualifications and Technical Skills: see full JD provided by user
"""


def find_resume_pdf():
    # project root is one level up from tests directory
    repo_root = Path(__file__).resolve().parents[1]
    candidates = [
        repo_root / "CV - Base.pdf",
        repo_root / "cv.pdf",
        repo_root / "resume.pdf",
    ]

    for p in candidates:
        if p.exists():
            return p
    return None


def main():
    pdf = find_resume_pdf()

    if not pdf:
        print("ERROR: No resume PDF found in repository root. Please place your resume PDF as 'CV - Base.pdf'.")
        sys.exit(1)

    print(f"Using resume PDF: {pdf}")

    payload = {
        "resume_pdf_path": str(pdf),
        "job_description": JOB_DESCRIPTION,
        "candidate_name": "Ibrahim Younis"
    }

    flow = InterviewCoachFlow()

    print("Starting InterviewCoachFlow... this may take a while depending on agent configuration.")
    flow.kickoff({"crewai_trigger_payload": payload})

    print("Flow finished. Check interview_results/ for saved session outputs.")


if __name__ == "__main__":
    main()
