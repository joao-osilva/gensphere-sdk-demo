import os
from dotenv import load_dotenv
from textwrap import dedent

from crewai import Crew, Agent, Task
from crewai_tools import WebsiteSearchTool, SerperDevTool

from gensphere_python_sdk.genpod_crewai import GenPodCrewAI

load_dotenv()

web_search_tool = WebsiteSearchTool()
seper_dev_tool = SerperDevTool()
						
def main():
    # Create Agents
    researcher_agent = Agent(
        role='Research Analyst',
        goal='Analyze the company website and provided description to extract insights on culture, values, and specific needs.',
        tools=[web_search_tool, seper_dev_tool],
        backstory='Expert in analyzing company cultures and identifying key values and needs from various sources, including websites and brief descriptions.',
        verbose=True
    )
    
    # Define Tasks for each agent
    research_company_culture_task = Task(
						description=dedent(f"""\
								Analyze the provided company website and the hiring manager's company's domain {company_domain}, description: "{company_description}". Focus on understanding the company's culture, values, and mission. Identify unique selling points and specific projects or achievements highlighted on the site.
								Compile a report summarizing these insights, specifically how they can be leveraged in a job posting to attract the right candidates."""),
						expected_output=dedent("""\
								A comprehensive report detailing the company's culture, values, and mission, along with specific selling points relevant to the job role. Suggestions on incorporating these insights into the job posting should be included."""),
						agent=researcher_agent)

    # Instantiate the crew with a sequential process
    crew = Crew(
        agents=[researcher_agent],
        tasks=[
            research_company_culture_task,
        ]
    )

    return  crew

if __name__ == "__main__":
    host, port = os.getenv("API_HOST"), os.getenv("API_PORT")
    
    GenPodCrewAI(main()).run(host, int(port))