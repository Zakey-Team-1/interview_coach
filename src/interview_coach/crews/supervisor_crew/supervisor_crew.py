# src/ai_interview_coach/crews/interview_crew/interview_crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from pydantic import BaseModel

class InterviewTopics(BaseModel):
    interview_topics: List[str]

@CrewBase
class SupervisorCrew():
    """Crew for conducting the live interview session"""

    agents_config: str = 'config/agents.yaml'
    tasks_config: str = 'config/tasks.yaml'
    
    agents: List[BaseAgent]
    tasks: List[Task]
    


    @agent
    def supervisor(self) -> Agent:
        return Agent(
            config=self.agents_config['supervisor'], # type: ignore[index]
            verbose=True
        )
        
    @task
    def create_interview_roadmap(self) -> Task:
        return Task(
            config=self.tasks_config['create_interview_roadmap'], # type: ignore[index]
            output_pydantic= InterviewTopics
        )

    @crew
    def crew(self) -> Crew:
        """Creates the interview execution crew"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )