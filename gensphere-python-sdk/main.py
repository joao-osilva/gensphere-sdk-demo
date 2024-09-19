from gensphere_python_sdk.AgenticFlow.AgenticFlow import AgenticFlow
from gensphere_python_sdk.AgenticFlow.yml_compose import YmlCompose
from dotenv import load_dotenv
import os
import logging
import pprint

#load_dotenv()
#OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# main.py

# Set up logging for main script
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Compose the YAML files into one combined data structure
    try:
        composer = YmlCompose('sample.yaml')
        combined_yaml_data = composer.compose(save_combined_yaml=True, output_file='combined.yaml')

        # Print the combined YAML data
        logger.info("Combined YAML Data:")
        pprint.pprint(combined_yaml_data)

        # Initialize AgenticFlow with the combined YAML data
        flow = AgenticFlow(combined_yaml_data)
        flow.parse_yaml()

        # Print the nodes parsed
        logger.info("Nodes parsed:")
        for node_name in flow.nodes:
            logger.info(f"- {node_name}")

        # Run the flow and print outputs
        flow.run()
        logger.info("Flow execution completed. Outputs:")
        for node_name, outputs in flow.outputs.items():
            logger.info(f"Node '{node_name}' outputs: {outputs}")

    except Exception as e:
        logger.error(f"An error occurred during flow execution: {e}")
