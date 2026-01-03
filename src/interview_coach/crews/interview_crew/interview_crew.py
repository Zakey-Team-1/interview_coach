# Interview Crew
"""
CrewAI crew for generating interview questions.
"""
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List


@CrewBase
class InterviewCrew():
    """
    Crew for generating interview questions.
    
    This crew is responsible for:
    - Generating contextual interview questions based on topics
    - Creating follow-up questions based on candidate responses
    """

    agents_config: str = 'config/agents.yaml'
    tasks_config: str = 'config/tasks.yaml'
    
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def interviewer(self) -> Agent:
        """The interviewer agent that generates questions."""
        return Agent(
            config=self.agents_config['interviewer'],  # type: ignore[index]
            verbose=True,
            allow_delegation=False,
            max_iter=5  # Limit iterations for faster responses
        )

    @task
    def conduct_interview_session(self) -> Task:
        """Task for generating a single interview question."""
        return Task(
            config=self.tasks_config['conduct_interview_session']  # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the interview question generation crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )