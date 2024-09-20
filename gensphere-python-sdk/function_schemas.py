# function_schemas.py

from pydantic import BaseModel, Field

class AnalyzeDataFunction(BaseModel):
    analysis: str = Field(
        description="The analysis of the processed data."
    )

    class Config:
        schema_extra = {
            "description": "Analyze the processed data and provide insights."
        }
