import os
import autogen
from dotenv import load_dotenv
from pydantic import BaseModel

from gensphere_python_sdk.genpod_autogen import GenPodAutoGen

load_dotenv()

class InputSchema(BaseModel):
    paper_topic: str

def main():
    llm_config = {
        "timeout": 600,
        "cache_seed": 44,
        "config_list": [{"model": "gpt-4", "api_key": os.getenv("OPENAI_API_KEY")}],
        "temperature": 0,
    }
    
    assistant = autogen.AssistantAgent(
        name="assistant",
        llm_config=llm_config,
        is_termination_msg=lambda x: True if "TERMINATE" in x.get("content") else False,
    )
    
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: True if "TERMINATE" in x.get("content") else False,
        max_consecutive_auto_reply=10,
        code_execution_config={
            "work_dir": "work_dir",
            "use_docker": False,
        },
    )

    task = """
    Find arxiv papers that show how are people studying {paper_topic} in AI based systems
    """

    return {
        GenPodAutoGen.ParamType.AGENT: user_proxy,
        GenPodAutoGen.ParamType.RECIPIENT: assistant,
        GenPodAutoGen.ParamType.MESSAGE: task
    }

if __name__ == "__main__":
    host, port = os.getenv("API_HOST"), os.getenv("API_PORT")
    
    GenPodAutoGen(
        agent = main(), 
        input_schema = InputSchema,
        ).run(host, int(port))