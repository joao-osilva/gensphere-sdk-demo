import uvicorn
from enum import Enum
from typing import Annotated, Dict, Any
from pydantic import BaseModel
from fastapi import Body, FastAPI, HTTPException
from autogen.agentchat import ConversableAgent, Agent
from autogen.agentchat.chat import ChatResult

from gensphere_python_sdk.logging_config import setup_logger

logger = setup_logger(__name__)

class GenPodAutoGen:
    class ParamType(Enum):
        AGENT = "agent"
        RECIPIENT = "recipient"
        MESSAGE = "message"

    def __init__(self, agent: Dict[str, Any], input_schema: BaseModel):
        self.agent = agent[self.ParamType.AGENT]
        self.recipient = agent[self.ParamType.RECIPIENT]
        self.message = agent[self.ParamType.MESSAGE]
        self.input_schema = input_schema
        self.app = FastAPI()
        self.setup_routes()
        
        
        logger.info("GenPodAutoGen initialized with agent: %s", self.agent.name)
    
    def run(self, host: str, port: int):
        uvicorn.run(self.app, host=host, port=port)

    def setup_routes(self):
        
        @self.app.post("/initiate_chat/")
        async def initiate_chat(input_data: Annotated[self.input_schema, Body()]) -> ChatResult:
            logger.info("Received request to initiate chat with inputs: %s", input_data.model_dump())
            try:

                result = self.agent.initiate_chat(
                    self.recipient, 
                    message=self.message.format(**input_data.model_dump())
                )
                logger.info("Chat completed with result: %s", result)
                return result
            except Exception as e: 
                logger.error("Error in initiate_chat endpoint: %s", str(e))
                raise HTTPException(status_code=500, detail="initiate_chat failed")