import yaml
import networkx as nx
import pandas as pd
import sqlite3
import requests
import re
import json
from jsonschema import validate, ValidationError
from importlib import import_module  # Used for dynamic tool imports


class AgenticFlow:
    def __init__(self, yaml_file_path, available_classes, openai_api_key, db_table_name=None):
        """
        Initializes the GraphExecutor.

        :param yaml_file_path: Path to the YAML file containing node dependencies and executors.
        :param available_classes: A dictionary mapping class names (strings) to actual class objects.
        :param openai_api_key: The OpenAI API key for authentication.
        :param db_table_name: The name of the AWS DynamoDB table to look up executors when needed (optional).
        """
        self.graph = nx.DiGraph()
        self.node_classes = {}
        self.results = {}
        self.db_table_name = db_table_name
        self.openai_api_key = openai_api_key

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

                # Optional fields that are not used by GraphExecutor
                description = details.get('description', '')
                output = details.get('output', '')

                if isinstance(executor_name, str) and self.is_url(executor_name):
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
                elif executor_name == "sql_executor":
                    # SQL Executor that processes data with SQL queries
                    self.node_classes[node] = {
                        "type": "sql_executor",
                        "args": args,
                        "kwargs": kwargs
                    }
                elif executor_name == "pandas_executor":
                    # Pandas executor that processes DataFrame methods dynamically
                    self.node_classes[node] = {
                        "type": "pandas_executor",
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
                    # If DynamoDB lookup is not being used, raise an error for unknown executors
                    raise ValueError(f"Executor '{executor_name}' not found in available classes or known sources.")

                # Add dependencies as edges in the graph
                dependencies = details.get('dependencies', [])
                for dependency in dependencies:
                    self.graph.add_edge(dependency, node)

    def is_url(self, value):
        """
        Checks if a value is a URL string.

        :param value: The value to check.
        :return: True if the value is a URL, False otherwise.
        """
        # Ensure the value is a string before checking for URL patterns
        return isinstance(value, str) and (value.startswith("http://") or value.startswith("https://"))

    def substitute_placeholders(self, value, results, convert_to_string=False):
        """
        Substitutes placeholders in a value with corresponding results.

        :param value: The value containing placeholders (could be string, list, or dict).
        :param results: The dictionary containing results of executed nodes.
        :param convert_to_string: If True, converts the result to string when substituting.
        :return: The value with placeholders replaced with actual results.
        """
        if isinstance(value, str):
            pattern = re.compile(r"{{\s*(\w+)\s*}}")
            matches = pattern.findall(value)
            for match in matches:
                if match in results:
                    replacement = results[match]
                    # Convert to string only if explicitly required for OpenAI, otherwise leave as is
                    replacement = str(replacement) if convert_to_string else replacement
                    # Only perform replace if the replacement is a string
                    if isinstance(replacement, str):
                        value = value.replace(f"{{{{ {match} }}}}", replacement)
                    else:
                        return replacement  # Directly return non-string objects like DataFrames
            return value
        elif isinstance(value, list):
            return [self.substitute_placeholders(item, results, convert_to_string) for item in value]
        elif isinstance(value, dict):
            return {key: self.substitute_placeholders(val, results, convert_to_string) for key, val in value.items()}
        else:
            return value

    def substitute_kwargs(self, kwargs, results, convert_to_string=False):
        """
        Substitutes placeholder references in kwargs with actual results from predecessors.

        :param kwargs: The keyword arguments with placeholders.
        :param results: The results of previously executed nodes.
        :param convert_to_string: If True, converts the result to string when substituting.
        :return: Updated kwargs with placeholders replaced with actual values.
        """
        return {key: self.substitute_placeholders(value, results, convert_to_string) for key, value in kwargs.items()}

    def run_node(self, node):
        """
        Runs a single node's executor and returns the result.

        :param node: The node to run.
        :return: The result of the node's execution.
        """
        result = None  # Initialize result with a default value to avoid unassigned access errors

        # Get predecessors (dependencies) of the current node
        predecessors = list(self.graph.predecessors(node))

        # Collect outputs of the dependencies
        inputs = [self.results[predecessor] for predecessor in predecessors]

        # Determine the type of executor and execute accordingly
        executor_info = self.node_classes[node]
        # Only convert to string for OpenAI executor; otherwise, pass outputs directly
        convert_to_string = executor_info["type"] == "openai"
        kwargs = self.substitute_kwargs(executor_info.get("kwargs", {}), self.results, convert_to_string)

        # Correct handling for cases where there are no predecessors (inputs)
        if executor_info["type"] == "class":
            # Call the run method of the class instance
            result = executor_info["executor"].run(*inputs, **kwargs)
        elif executor_info["type"] == "sql_executor":
            # Handle the case where sql_executor might need a default input
            # Ensure 'table_path' is not duplicated in kwargs
            table_path = inputs[0] if inputs else kwargs.pop("table_path", None)
            if table_path is None or (isinstance(table_path, str) and not table_path.strip()):
                raise ValueError("Table path is required for SQL execution and must not be empty.")
            if "table_path" in kwargs:
                del kwargs["table_path"]  # Ensure table_path is removed from kwargs
            result = self.run_sql_executor(table_path=table_path, **kwargs)
        elif executor_info["type"] == "pandas_executor":
            # Handle the case where pandas_executor might need a default input
            input_df = inputs[0] if inputs else None
            result = self.run_pandas_executor(input_df=input_df, **kwargs)
        elif executor_info["type"] == "openai":
            # Run OpenAI executor, no specific input dependency required
            result = self.run_openai_executor(**kwargs)
        else:
            # Handle cases where the executor type is not recognized
            raise ValueError(f"Unknown executor type for node '{node}'.")

        # Save the result
        self.results[node] = result
        return result

    def run_sql_executor(self, table_path=None, query=None, output_path=None):
        """
        Executes an SQL query on a table provided by a path or DataFrame.

        :param table_path: The path to the table (can be an output of another node, local file, or database API address or DataFrame).
        :param query: The SQL query to run.
        :param output_path: Optional path to save the output table.
        :return: Resulting DataFrame from the query.
        """
        # Ensure table_path is correctly checked and not ambiguously evaluated
        if table_path is None:
            raise ValueError("Table path is required for SQL execution.")

        # Check if table_path is a DataFrame directly passed as output from another node
        if isinstance(table_path, pd.DataFrame):
            df = table_path
        elif self.is_url(table_path):
            raise NotImplementedError("Accessing remote databases via API is not implemented in this demo.")
        elif isinstance(table_path, str) and table_path.strip():
            try:
                df = pd.read_csv(table_path)  # Read the CSV file
            except Exception as e:
                print(f"Error reading table from path {table_path}: {e}")
                raise
        else:
            raise ValueError(f"Invalid table path type: {type(table_path)}. Expected DataFrame, URL, or file path.")

        try:
            conn = sqlite3.connect(":memory:")  # Use in-memory SQLite database
            table_name = "data_table"  # Change table name to avoid SQL reserved keyword conflict
            df.to_sql(table_name, conn, index=False, if_exists='replace')  # Load into SQL with new table name
            result_df = pd.read_sql_query(query, conn)  # Execute the query
            conn.close()

            # Save result if output path is provided
            if output_path:
                result_df.to_csv(output_path, index=False)

            return result_df
        except Exception as e:
            print(f"Error executing SQL: {e}")
            raise

    def run_pandas_executor(self, input_df=None, method=None, input_path=None, output_path=None):
        """
        Executes a specified method on a Pandas DataFrame and optionally saves the output.

        :param input_df: The DataFrame to modify, or None if loading from input_path.
        :param method: A string representing the Pandas method to apply to the DataFrame.
        :param input_path: Optional path to load the input DataFrame.
        :param output_path: Optional path to save the modified DataFrame.
        :return: Modified DataFrame after applying the method.
        """
        try:
            # Load DataFrame from input_path if no input DataFrame is provided
            if input_df is None and input_path:
                df = pd.read_csv(input_path)
                print(f"DataFrame loaded from {input_path}")
            else:
                # Use the passed DataFrame if no input path is specified
                df = input_df

            if df is None:
                raise ValueError("No DataFrame provided for pandas_executor execution.")

            # Dynamically apply the method to the DataFrame
            if method.startswith(".apply"):
                # Handling the .apply() case safely
                df = df.apply(eval(method[6:]))  # Apply the method by evaluating the lambda function part safely
            else:
                # Use getattr to safely apply the method to the DataFrame
                method_name = method.split('(')[0].lstrip('.')
                if hasattr(df, method_name):
                    df = getattr(df, method_name)()

            # Save the result to the specified path if provided
            if output_path:
                df.to_csv(output_path, index=False)
                print(f"DataFrame saved to {output_path}")

            return df
        except Exception as e:
            print(f"Error applying method to DataFrame: {e}")
            raise

    def run_openai_executor(self, model, messages, structured_output=False, schema=None, tool_name=None):
        """
        Makes an API call to the OpenAI Chat Completions API, optionally using a tool.

        :param model: The model to use (e.g., "gpt-3.5-turbo").
        :param messages: A list of message dictionaries for the API call.
        :param structured_output: If True, parses the response as structured output (JSON).
        :param schema: The schema to validate the structured output against.
        :param tool_name: Optional tool name to use for calculations or enhancements.
        :return: The response from the API, parsed if structured output is expected.
        """
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages
        }

        # Dynamically load and execute the tool if specified
        tool_result = None
        if tool_name:
            try:
                tool_module = import_module("tools")  # Import the module where the tool is defined
                tool_function = getattr(tool_module, tool_name)  # Get the tool function by name
                tool_result = tool_function(10)  # Example of how tool might be used with a placeholder input
                print(f"Tool '{tool_name}' executed with result: {tool_result}")
            except (ModuleNotFoundError, AttributeError) as e:
                print(f"Error loading tool '{tool_name}': {e}")

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            response_content = response.json()["choices"][0]["message"]["content"]

            # Handle structured output parsing and schema validation if specified
            if structured_output:
                try:
                    result = json.loads(response_content)
                    if schema:
                        # Validate the response against the provided schema
                        validate(instance=result, schema=schema)
                    print(f"Structured Output from OpenAI: {result}")
                    return result
                except json.JSONDecodeError:
                    print(f"Failed to parse structured output. Returning raw response.")
                    return response_content
                except ValidationError as ve:
                    print(f"Schema validation error: {ve}")
                    raise ValueError("Output from OpenAI did not match the expected schema.")
            else:
                print(f"Output from OpenAI: {response_content}")
                return response_content
        except Exception as e:
            print(f"Error during OpenAI API call: {e}")
            raise

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
                self.run_node(node)
            except Exception as e:
                print(f"Error executing node {node}: {e}")

