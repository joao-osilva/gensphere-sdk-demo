import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crewai import Crew

from gensphere_python_sdk.logging_config import setup_logger

logger = setup_logger(__name__)

class KickoffInput(BaseModel):
    data: dict

class GenPodCrewAI:
    def __init__(self, crew: Crew):
        self.app = FastAPI()
        self.setup_routes()
        self.crew = crew
        
        logger.info("GenPodCrewAI initialized with crew: %s", self.crew.name)
    
    def run(self, host: str, port: int):
        uvicorn.run(self.app, host=host, port=port)

    def setup_routes(self):
        
        @self.app.post("/kickoff")
        async def kickoff_crew(input_data: KickoffInput):
            logger.info("Received request to kickoff with inputs: %s", input_data)
            try:

                result = self.crew.kickoff(inputs = input_data.data)
                logger.info("Kickoff completed with result: %s", result)
                return {"result": result}
            except Exception as e: 
                logger.error("Error in kickoff endpoint: %s", str(e))
                raise HTTPException(status_code=500, detail="Kickoff failed")