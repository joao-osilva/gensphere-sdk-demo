import yaml
import networkx as nx
import requests
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import re

# Assume OpenAI API Key is set in the environment variable 'OPENAI_API_KEY'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class AgenticFlow:
    def __init__(self, yaml_file_path, available_classes, db_table_name):
        """
        Initializes the GraphExecutor.

        :param yaml_file_path: Path to the YAML file containing node dependencies and executors.
        :param available_classes: A dictionary mapping class names (strings) to actual class objects.
        :param db_table_name: The name of the AWS DynamoDB table to look up executors when needed.
        """
        self.graph = nx.DiGraph()
        self.node_classes = {}
        self.results = {}
        self.db_table_name = db_table_name

        # AWS DynamoDB client
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(db_table_name)

        # Load graph structure from the YAML file and initialize classes
        self.load_graph_from_yaml(yaml_file_path, available_classes)

    def load_graph_from_yaml(self, yaml_file_path, available_classes):
        """
        Loads nodes, their dependencies, and executors from a YAML file, then builds the graph.

        :param yaml_file_path: Path to the YAML file.
        :param available_classes: A dictionary mapping class names (strings) to class objects.
        """
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file)
            nodes = data.get('nodes', {})

            # Add nodes, their executors, and dependencies to the graph
            for node, details in nodes.items():
                executor_name = details.get('executor')
                executor_args = details.get('executor_args', {})
                args = executor_args.get('args', [])
                kwargs = executor_args.get('kwargs', {})

                if self.is_url(executor_name):
                    # Executor is a direct URL (local or otherwise)
                    self.node_classes[node] = {
                        "type": "url",
                        "executor": executor_name,
                        "args": args,
                        "kwargs": kwargs
                    }
                elif executor_name == "openai":
                    # Special case for OpenAI Chat Completions API
                    self.node_classes[node] = {
                        "type": "openai",
                        "args": args,
                        "kwargs": kwargs
                    }
                elif executor_name in available_classes:
                    # Initialize the executor class with the provided arguments
                    self.node_classes[node] = {
                        "type": "class",
                        "executor": available_classes[executor_name](*args, **kwargs),
                    }
                else:
                    # Fetch URL details from AWS DynamoDB
                    try:
                        response = self.table.get_item(Key={'executor_id': executor_name})
                        if 'Item' not in response:
                            raise ValueError(f"No entry found in the database for executor '{executor_name}'")

                        # Extract the URL from the DynamoDB entry
                        url = response['Item'].get('url')
                        if not url:
                            raise ValueError(f"URL not found for executor '{executor_name}' in the database")

                        # Store the URL and arguments for later execution
                        self.node_classes[node] = {
                            "type": "url",
                            "executor": url,
                            "args": args,
                            "kwargs": kwargs
                        }

                    except (NoCredentialsError, ClientError) as e:
                        print(f"Error accessing AWS DynamoDB: {e}")
                        raise

                # Add dependencies as edges in the graph
                dependencies = details.get('dependencies', [])
                for dependency in dependencies:
                    self.graph.add_edge(dependency, node)

    def is_url(self, string):
        """
        Checks if a string is a URL.

        :param string: The string to check.
        :return: True if the string is a URL, False otherwise.
        """
        return string.startswith("http://") or string.startswith("https://")

    def substitute_kwargs(self, kwargs, results):
        """
        Substitutes placeholder references in kwargs with actual results from predecessors.

        :param kwargs: The keyword arguments with placeholders.
        :param results: The results of previously executed nodes.
        :return: Updated kwargs with placeholders replaced with actual values.
        """
        updated_kwargs = {}
        pattern = re.compile(r"{{\s*(\w+)\s*}}")  # Pattern to match {{ node_name }}

        for key, value in kwargs.items():
            if isinstance(value, str):
                # Substitute placeholder with the corresponding result
                match = pattern.match(value)
                if match:
                    referenced_node = match.group(1)
                    if referenced_node in results:
                        updated_kwargs[key] = results[referenced_node]
                    else:
                        raise ValueError(f"Referenced node '{referenced_node}' has not been executed yet.")
                else:
                    updated_kwargs[key] = value
            else:
                updated_kwargs[key] = value

        return updated_kwargs

    def run_node(self, node):
        """
        Runs a single node's executor and returns the result.

        :param node: The node to run.
        :return: The result of the node's execution.
        """
        # Get predecessors (dependencies) of the current node
        predecessors = list(self.graph.predecessors(node))

        # Collect outputs of the dependencies
        inputs = [self.results[predecessor] for predecessor in predecessors]

        # Determine the type of executor and execute accordingly
        executor_info = self.node_classes[node]
        kwargs = self.substitute_kwargs(executor_info.get("kwargs", {}), self.results)

        if executor_info["type"] == "class":
            # Call the run method of the class instance
            return executor_info["executor"].run(*inputs, **kwargs)
        elif executor_info["type"] == "url":
            # Make an API request to the URL with the inputs and additional arguments
            url = executor_info["executor"]
            args = executor_info["args"]
            response = requests.post(url, json={"inputs": inputs, *args, **kwargs})
            response.raise_for_status()  # Raise an error for bad responses
            return response.json()  # Assumes the response is in JSON format
        elif executor_info["type"] == "openai":
            # Make an API call to the OpenAI Chat Completions API
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": kwargs.get("model", "gpt-3.5-turbo"),
                "messages": kwargs.get("messages", [])
            }
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    def execute(self):
        """
        Executes the nodes in the graph sequentially in topological order.
        """
        try:
            # Perform topological sort to get the order of execution
            sorted_nodes = list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible:
            raise ValueError("The graph contains a cycle and is not a DAG.")

        # Execute each node sequentially in the sorted order
        for node in sorted_nodes:
            try:
                self.results[node] = self.run_node(node)
            except Exception as e:
                print(f"Error executing node {node}: {e}")