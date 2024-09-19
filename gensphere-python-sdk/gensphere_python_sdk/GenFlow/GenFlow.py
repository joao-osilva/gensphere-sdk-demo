# GenFlow.py

import yaml
import jinja2
import networkx as nx
import importlib
import traceback
import logging
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json
from openai import OpenAI

# Load environment variables
load_dotenv()

# Module-level logger
logger = logging.getLogger(__name__)

class GenFlow:
    """
    Class to parse YAML data, construct an execution graph, and execute nodes.
    """

    def __init__(self, yaml_data):
        self.yaml_data = yaml_data
        self.nodes = {}        # Maps node names to Node instances
        self.outputs = {}      # Stores outputs from nodes
        self.graph = nx.DiGraph()
        self.env = jinja2.Environment()
        self.variables = {}    # For storing variables across nodes
        self.variable_producers = {}  # Maps variable names to node names

        # Initialize OpenAI client with API key from environment variable
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=api_key)

        logger.debug("GenFlow initialized.")

    def parse_yaml(self):
        """
        Parses the YAML data and constructs nodes.
        """
        data = self.yaml_data
        logger.info("Parsing YAML data")
        for node_data in data.get('nodes', []):
            node = Node(node_data)
            logger.info(f"Adding node '{node.name}' of type '{node.type}'")
            if node.name in self.nodes:
                raise ValueError(f"Duplicate node name '{node.name}' found.")
            self.nodes[node.name] = node

            # Record variables produced by the node
            produced_variables = node.get_produced_variables()
            for var_name in produced_variables:
                if var_name in self.variable_producers:
                    raise ValueError(f"Variable '{var_name}' is set by multiple nodes.")
                self.variable_producers[var_name] = node.name

        # Build the execution graph
        self.build_graph()

    def build_graph(self):
        """
        Builds the execution graph based on node dependencies.
        """
        logger.info("Building execution graph")
        for node in self.nodes.values():
            self.graph.add_node(node.name)
            logger.debug(f"Added node '{node.name}' to graph")

        for node in self.nodes.values():
            dependencies = node.get_dependencies()
            logger.debug(f"Node '{node.name}' dependencies: {dependencies}")
            for dep in dependencies:
                if dep in self.nodes:
                    self.graph.add_edge(dep, node.name)
                    logger.debug(f"Added edge from node '{dep}' to '{node.name}'")
                elif dep in self.variable_producers:
                    producer_node = self.variable_producers[dep]
                    self.graph.add_edge(producer_node, node.name)
                    logger.debug(f"Added edge from variable producer '{producer_node}' to '{node.name}'")
                else:
                    logger.error(f"Node '{node.name}' depends on undefined node or variable '{dep}'")
                    raise ValueError(f"Node '{node.name}' depends on undefined node or variable '{dep}'.")
        # Check for cycles
        if not nx.is_directed_acyclic_graph(self.graph):
            logger.error("The execution graph has cycles. Cannot proceed.")
            raise ValueError("The execution graph has cycles. Cannot proceed.")

    def run(self):
        """
        Executes the nodes in topological order.
        """
        try:
            execution_order = list(nx.topological_sort(self.graph))
            logger.info(f"Execution order: {execution_order}")
        except nx.NetworkXUnfeasible:
            logger.error("Graph has cycles, cannot proceed.")
            raise Exception("Graph has cycles, cannot proceed.")

        for node_name in execution_order:
            node = self.nodes[node_name]
            node.set_flow(self)  # Set the reference to the GenFlow instance

            # Render parameters
            try:
                logger.info(f"Rendering parameters for node '{node_name}'")
                params = node.render_params(self.outputs, self.env)
                logger.debug(f"Parameters for node '{node_name}': {params}")
            except Exception as e:
                logger.error(f"Error rendering params for node '{node_name}': {e}")
                traceback.print_exc()
                continue  # Skip execution of this node

            # Execute node
            try:
                logger.info(f"Executing node '{node_name}'")
                outputs = node.execute(params)
                # Validate outputs
                if not isinstance(outputs, dict):
                    raise ValueError(f"Node '{node_name}' did not return a dictionary of outputs.")
                expected_outputs = set(node.outputs)
                actual_outputs = set(outputs.keys())
                if expected_outputs != actual_outputs:
                    raise ValueError(
                        f"Node '{node_name}' outputs {actual_outputs} do not match expected outputs {expected_outputs}."
                    )
                # Save outputs
                self.outputs[node_name] = outputs
                logger.info(f"Outputs of node '{node_name}': {outputs}")
            except Exception as e:
                logger.error(f"Error executing node '{node_name}': {e}")
                traceback.print_exc()
                continue  # Skip saving outputs for this node

class Node:
    """
    Represents an operation node in the execution graph.
    """

    def __init__(self, node_data):
        self.name = node_data['name']
        self.type = node_data['type']
        self.node_data = node_data
        self.outputs = node_data.get('outputs', [])
        self.flow = None  # Reference to the GenFlow instance
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    def set_flow(self, flow):
        """
        Sets the reference to the GenFlow instance.

        Args:
            flow (GenFlow): The GenFlow instance.
        """
        self.flow = flow

    def get_dependencies(self):
        """
        Extracts dependencies from the parameters and variables.

        Returns:
            set: A set of node or variable names that this node depends on.
        """
        dependencies = set()
        params = self.node_data.get('params', {})
        for value in params.values():
            dependencies.update(self.extract_dependencies_from_value(value))

        # Handle specific dependencies for different node types
        if self.type == 'get_variables':
            # For get_variables nodes, add dependencies from 'variables' field
            variables = self.node_data.get('variables', {})
            for var_name in variables.values():
                dependencies.add(var_name)
        elif self.type == 'set_variable':
            # For set_variable nodes, check if 'value' depends on any variables
            value = params.get('value')
            if value:
                dependencies.update(self.extract_dependencies_from_value(value))

        return dependencies

    @staticmethod
    def extract_dependencies_from_value(value):
        """
        Extracts node and variable names from templated values.

        Args:
            value: The parameter value to inspect.

        Returns:
            set: A set of node or variable names referenced in the value.
        """
        import re
        pattern = r"\{\{\s*([\w_\.]+)\s*\}\}"
        matches = re.findall(pattern, str(value))
        dependencies = set()
        for match in matches:
            var_parts = match.split('.')
            dependencies.add(var_parts[0])
        return dependencies

    def get_produced_variables(self):
        """
        Returns a list of variables produced by this node.
        """
        if self.type == 'set_variable':
            return [self.node_data['variable_name']]
        else:
            return []

    def render_params(self, outputs, env):
        """
        Renders the parameters with values from previous outputs.

        Args:
            outputs (dict): Outputs from previously executed nodes.
            env (jinja2.Environment): Jinja2 environment for templating.

        Returns:
            dict: Rendered parameters ready for execution.
        """
        params = self.node_data.get('params', {})
        # Build the context with outputs accessible by node name
        context = {}
        for node_name, node_outputs in outputs.items():
            context[node_name] = node_outputs
        # Add variables to context
        context.update(self.flow.variables)
        # Render each parameter individually
        rendered_params = {}
        for key, value in params.items():
            if isinstance(value, str):
                # Check if the value is a simple variable reference
                import re
                simple_var_pattern = r"^\{\{\s*([\w_\.]+)\s*\}\}$"
                match = re.match(simple_var_pattern, value)
                if match:
                    var_name = match.group(1)
                    # Split var_name to access nested variables
                    var_parts = var_name.split('.')
                    obj = context
                    try:
                        for part in var_parts:
                            if isinstance(obj, dict):
                                obj = obj[part]
                            else:
                                obj = getattr(obj, part)
                        rendered_params[key] = obj
                    except (KeyError, AttributeError, TypeError) as e:
                        # Variable not found in context
                        raise ValueError(f"Variable '{var_name}' not found in context.") from e
                else:
                    # Use Jinja2 rendering for other cases
                    template = env.from_string(value)
                    rendered_value = template.render(**context)
                    rendered_params[key] = rendered_value
            else:
                # Non-string params are used as is
                rendered_params[key] = value
        return rendered_params

    def execute(self, params):
        """
        Executes the node based on its type and parameters.

        Args:
            params (dict): Parameters for the node execution.

        Returns:
            dict: Outputs from the node execution.
        """
        self.logger.debug(f"Executing node of type '{self.type}' with params: {params}")
        if self.type == 'function_call':
            return self.execute_function_call(params)
        elif self.type == 'llm_service':
            return self.execute_llm_service(params)
        elif self.type == 'set_variable':
            return self.execute_set_variable(params)
        elif self.type == 'get_variable':
            return self.execute_get_variable(params)
        elif self.type == 'get_variables':
            return self.execute_get_variables(params)
        else:
            raise NotImplementedError(f"Type '{self.type}' not implemented for node '{self.name}'.")

    def execute_function_call(self, params):
        """
        Executes a function call node.

        Args:
            params (dict): Parameters for the function.

        Returns:
            dict: Dictionary of outputs from the function.
        """
        try:
            module = importlib.import_module('functions')
            func = getattr(module, self.node_data['function'])
        except ImportError as e:
            raise ImportError(f"Error importing module 'functions': {e}")
        except AttributeError as e:
            raise AttributeError(f"Function '{self.node_data['function']}' not found in 'functions' module.")

        # Execute function with parameters
        result = func(**params)
        if not isinstance(result, dict):
            raise ValueError(f"Function '{self.node_data['function']}' should return a dictionary of outputs.")
        # Ensure result keys match outputs
        expected_outputs = set(self.outputs)
        actual_outputs = set(result.keys())
        if expected_outputs != actual_outputs:
            raise ValueError(
                f"Function outputs {actual_outputs} do not match expected outputs {expected_outputs}."
            )
        return result

    def execute_llm_service(self, params):
        """
        Executes an LLM service node.

        Args:
            params (dict): Parameters for the LLM service.

        Returns:
            dict: Dictionary of outputs from the LLM service.
        """
        service = self.node_data['service']
        if service == 'openai':
            return self.execute_openai_service(params)
        else:
            raise NotImplementedError(f"LLM service '{service}' not implemented for node '{self.name}'.")

    def execute_openai_service(self, params):
        """
        Executes an OpenAI LLM service call using the chat completions API.

        Args:
            params (dict): Parameters for the LLM service.

        Returns:
            dict: Dictionary of outputs from the LLM service.
        """
        model = self.node_data.get('model')
        function_call = self.node_data.get('function_call')

        if function_call:
            function_name = function_call['name']
            # Use the function schema defined in the function_schemas module
            function_schema = get_function_schema(function_name)

            # Prepare the tools (function definitions)
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "description": function_schema.get('description', ''),
                        "parameters": function_schema.get('parameters', {}),
                    },
                }
            ]

            # Prepare messages
            messages = [
                {"role": "user", "content": params['prompt']}
            ]

            # Call OpenAI API
            response = self.flow.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            # Handle response
            assistant_message = response.choices[0].message

            if assistant_message.tool_calls:
                tool_call = assistant_message.tool_calls[0]
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                # Optionally, execute the function here
                # For now, we can return the function call arguments as the output
                return {self.outputs[0]: arguments}
            else:
                # The model didn't call a function, return its content
                result = assistant_message.content
                if len(self.outputs) != 1:
                    raise ValueError(
                        f"Node '{self.name}' expects {len(self.outputs)} outputs, but OpenAI service returned 1."
                    )
                return {self.outputs[0]: result}
        else:
            # Simple prompt completion
            messages = [{"role": "user", "content": params['prompt']}]
            response = self.flow.client.chat.completions.create(
                model=model,
                messages=messages
            )
            assistant_message = response.choices[0].message
            result = assistant_message.content
            if len(self.outputs) != 1:
                raise ValueError(
                    f"Node '{self.name}' expects {len(self.outputs)} outputs, but OpenAI service returned 1."
                )
            return {self.outputs[0]: result}

    def execute_set_variable(self, params):
        """
        Sets a variable in the flow's variable store.

        Args:
            params (dict): Should contain 'value'.

        Returns:
            dict: Empty dictionary as no outputs.
        """
        variable_name = self.node_data['variable_name']
        value = params['value']
        # Store the variable in the GenFlow's variable store
        self.flow.variables[variable_name] = value
        return {}

    def execute_get_variable(self, params):
        """
        Retrieves a variable from the flow's variable store.

        Args:
            params (dict): Not used.

        Returns:
            dict: Dictionary containing the variable's value under the specified output name.
        """
        variable_name = self.node_data['variable_name']
        value = self.flow.variables.get(variable_name)
        if value is None:
            raise ValueError(f"Variable '{variable_name}' not found.")
        output_name = self.outputs[0] if self.outputs else 'value'
        return {output_name: value}

    def execute_get_variables(self, params):
        """
        Retrieves multiple variables from the flow's variable store.

        Args:
            params (dict): Not used.

        Returns:
            dict: Dictionary containing the variables' values under the specified output names.
        """
        variables = self.node_data['variables']  # This is a dict mapping output names to variable names
        result = {}
        for output_name, variable_name in variables.items():
            value = self.flow.variables.get(variable_name)
            if value is None:
                raise ValueError(f"Variable '{variable_name}' not found.")
            result[output_name] = value
        return result

def get_function_schema(function_name):
    """
    Retrieves the function schema for a function by name.

    Args:
        function_name (str): The name of the function schema.

    Returns:
        dict: The function definition, including name, description, parameters.
    """
    try:
        module = importlib.import_module('function_schemas')
        schema_class = getattr(module, function_name)
        # Get the JSON schema from Pydantic
        schema = schema_class.schema()
        # Build the function definition
        function_def = {
            "name": function_name,
            "description": schema.get('description', ''),
            "parameters": schema
        }
        return function_def
    except ImportError as e:
        raise ImportError(f"Error importing module 'function_schemas': {e}")
    except AttributeError as e:
        raise AttributeError(f"Function schema '{function_name}' not found in 'function_schemas' module.")
