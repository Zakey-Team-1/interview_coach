# src/ai_interview_coach/crews/evaluation_crew/evaluation_crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

@CrewBase
class EvaluationCrew():
    """Crew for analyzing performance and growth"""

    agents_config: str = 'config/agents.yaml'
    tasks_config: str = 'config/tasks.yaml'
    
    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def evaluator(self) -> Agent:
        return Agent(
            config=self.agents_config['evaluator'], # type: ignore[index]
            verbose=True
        )

    @task
    def evaluate_performance(self) -> Task:
        return Task(
            config=self.tasks_config['evaluate_performance'] # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the evaluation and reporting crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )