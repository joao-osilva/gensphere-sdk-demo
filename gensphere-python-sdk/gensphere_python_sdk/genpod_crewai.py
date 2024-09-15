import uvicorn
from typing import Annotated
from pydantic import BaseModel
from fastapi import Body, FastAPI, HTTPException
from crewai import Crew

from gensphere_python_sdk.logging_config import setup_logger

logger = setup_logger(__name__)

class GenPodCrewAI:
    def __init__(self, crew: Crew, input_schema: BaseModel, output_schema: BaseModel):
        self.crew = crew        
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.app = FastAPI()
        self.setup_routes()
        
        
        logger.info("GenPodCrewAI initialized with crew: %s", self.crew.name)
    
    def run(self, host: str, port: int):
        uvicorn.run(self.app, host=host, port=port)

    def setup_routes(self):
        
        @self.app.post("/kickoff/")
        async def kickoff(input_data: Annotated[self.input_schema, Body()]) -> self.output_schema:
            logger.info("Received request to kickoff with inputs: %s", input_data.model_dump())
            try:

                result = self.crew.kickoff(inputs = input_data.model_dump())
                logger.info("Kickoff completed with result: %s", result)
                return result.json_dict
            except Exception as e: 
                logger.error("Error in kickoff endpoint: %s", str(e))
                raise HTTPException(status_code=500, detail="Kickoff failed")