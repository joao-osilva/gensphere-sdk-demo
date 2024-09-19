# yml_compose.py

import yaml
import os
import logging

# Module-level logger
logger = logging.getLogger(__name__)

class YmlCompose:
    """
    Class to compose YAML files by resolving references to other YAML files.
    """

    def __init__(self, yaml_file):
        self.yaml_file = yaml_file
        self.combined_data = {'nodes': []}
        self.node_name_set = set()  # To keep track of all node names to avoid duplicates.

    def compose(self, save_combined_yaml=False, output_file='combined.yaml'):
        """
        Starts the composition process and returns the combined YAML data.

        Args:
            save_combined_yaml (bool): If True, saves the combined YAML data to a file.
            output_file (str): The filename to save the combined YAML data.
        """
        logger.info(f"Starting composition with root YAML file '{self.yaml_file}'")
        self._process_yaml_file(self.yaml_file)
        logger.info("Composition completed")

        if save_combined_yaml:
            with open(output_file, 'w') as f:
                yaml.dump(self.combined_data, f)
            logger.info(f"Combined YAML saved to '{output_file}'")

        return self.combined_data

    def _process_yaml_file(self, yaml_file, parent_prefix=''):
        """
        Recursively processes a YAML file, resolving any sub-flow references.

        Args:
            yaml_file (str): Path to the YAML file.
            parent_prefix (str): Prefix to be added to node names for uniqueness.
        """
        logger.info(f"Processing YAML file '{yaml_file}' with prefix '{parent_prefix}'")
        if not os.path.exists(yaml_file):
            logger.error(f"YAML file '{yaml_file}' does not exist.")
            raise FileNotFoundError(f"YAML file '{yaml_file}' does not exist.")

        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)

        if 'nodes' not in data:
            logger.error(f"YAML file '{yaml_file}' must contain 'nodes'.")
            raise ValueError(f"YAML file '{yaml_file}' must contain 'nodes'.")

        nodes = data['nodes']
        for node_data in nodes:
            node_type = node_data.get('type')
            node_name = node_data.get('name')
            if not node_name:
                logger.error("A node without a 'name' was found.")
                raise ValueError("A node without a 'name' was found.")

            # Create a unique node name by prefixing
            unique_node_name = parent_prefix + node_name
            logger.info(f"Processing node '{node_name}' (unique name: '{unique_node_name}') of type '{node_type}'")
            if unique_node_name in self.node_name_set:
                logger.error(f"Duplicate node name '{unique_node_name}' detected.")
                raise ValueError(f"Duplicate node name '{unique_node_name}' detected.")

            self.node_name_set.add(unique_node_name)

            if node_type == 'yml_flow':
                # Handle sub-flow
                sub_flow_file = node_data.get('yml_file')
                if not sub_flow_file:
                    logger.error(f"Node '{unique_node_name}' of type 'yml_flow' must have a 'yml_file' field.")
                    raise ValueError(f"Node '{unique_node_name}' of type 'yml_flow' must have a 'yml_file' field.")

                # Compute the absolute path of the sub-flow file
                sub_flow_file_path = os.path.join(os.path.dirname(yaml_file), sub_flow_file)
                logger.info(f"Sub-flow file for node '{unique_node_name}' is '{sub_flow_file_path}'")

                # Recursively process the sub-flow
                sub_flow_prefix = unique_node_name + '__'  # Use '__' as a separator
                self._process_yaml_file(sub_flow_file_path, parent_prefix=sub_flow_prefix)

                # Create parameter injection nodes
                param_injection_nodes = self._create_param_injection_nodes(node_data, sub_flow_prefix)
                self.combined_data['nodes'].extend(param_injection_nodes)
                logger.info(f"Added parameter injection nodes for '{unique_node_name}'")

                # Create a node to extract outputs from the sub-flow under the parent node's name
                output_extraction_node = self._create_output_extraction_node(node_data, sub_flow_prefix, unique_node_name)
                self.combined_data['nodes'].append(output_extraction_node)
                logger.info(f"Added output extraction node for '{unique_node_name}'")

            else:
                # Copy node data and adjust the name
                node_data = node_data.copy()
                node_data['name'] = unique_node_name

                # Adjust parameter references to account for prefixed node names
                node_data['params'] = self._adjust_params(node_data.get('params', {}), parent_prefix)
                logger.debug(f"Adjusted parameters for node '{unique_node_name}': {node_data['params']}")

                # Adjust variable names for 'set_variable' and 'get_variable' nodes
                if node_type in ['set_variable', 'get_variable']:
                    variable_name = node_data.get('variable_name')
                    if variable_name:
                        node_data['variable_name'] = parent_prefix + variable_name

                # Adjust variable mappings for 'get_variables' nodes
                if node_type == 'get_variables':
                    variables = node_data.get('variables', {})
                    adjusted_variables = {}
                    for output_name, variable_name in variables.items():
                        adjusted_variables[output_name] = parent_prefix + variable_name
                    node_data['variables'] = adjusted_variables

                # Add the node to the combined data
                self.combined_data['nodes'].append(node_data)
                logger.info(f"Added node '{unique_node_name}' to combined data")

    def _create_param_injection_nodes(self, node_data, sub_flow_prefix):
        """
        Creates nodes to inject parameters into the sub-flow.

        Args:
            node_data (dict): The original 'yml_flow' node data.
            sub_flow_prefix (str): The prefix used for sub-flow nodes.

        Returns:
            list: A list of nodes that inject parameters into the sub-flow.
        """
        injection_nodes = []
        params = node_data.get('params', {})
        for param_name, param_value in params.items():
            # Create a node that sets a parameter in the sub-flow
            injection_node = {
                'name': f"{sub_flow_prefix}inject_param_{param_name}",
                'type': 'set_variable',
                'variable_name': f"{sub_flow_prefix}{param_name}",
                'params': {
                    'value': param_value
                },
                'outputs': []
            }
            if injection_node['name'] in self.node_name_set:
                logger.error(f"Duplicate injection node name '{injection_node['name']}' detected.")
                raise ValueError(f"Duplicate injection node name '{injection_node['name']}' detected.")
            self.node_name_set.add(injection_node['name'])
            injection_nodes.append(injection_node)
        return injection_nodes

    def _create_output_extraction_node(self, node_data, sub_flow_prefix, parent_node_name):
        """
        Creates a node to extract outputs from the sub-flow and make them available under the parent node's name.

        Args:
            node_data (dict): The original 'yml_flow' node data.
            sub_flow_prefix (str): The prefix used for sub-flow nodes.
            parent_node_name (str): The unique name of the parent node.

        Returns:
            dict: A node that extracts outputs from the sub-flow.
        """
        outputs = node_data.get('outputs', [])
        variables = {output_name: f"{sub_flow_prefix}{output_name}" for output_name in outputs}
        extraction_node = {
            'name': parent_node_name,  # Use the parent node's unique name
            'type': 'get_variables',
            'variables': variables,
            'outputs': outputs
        }
        return extraction_node

    def _adjust_params(self, params, parent_prefix):
        """
        Adjusts parameter references to use prefixed node names and variables.

        Args:
            params (dict): The parameters to adjust.
            parent_prefix (str): The prefix for node names.

        Returns:
            dict: The adjusted parameters.
        """
        import re

        adjusted_params = {}
        pattern = r"(\{\{\s*)([\w_\.]+)(\s*\}\})"

        for key, value in params.items():
            if isinstance(value, str):
                def replace_func(match):
                    full_match = match.group(0)
                    prefix = match.group(1)
                    reference = match.group(2)
                    suffix = match.group(3)

                    # Split the reference into parts
                    parts = reference.split('.')
                    first_part = parts[0]
                    rest_parts = parts[1:]

                    # Adjust the first part (node or variable name)
                    if parent_prefix + first_part in self.node_name_set:
                        adjusted_first_part = parent_prefix + first_part
                    else:
                        adjusted_first_part = parent_prefix + first_part

                    adjusted_reference = '.'.join([adjusted_first_part] + rest_parts)

                    return prefix + adjusted_reference + suffix

                adjusted_value = re.sub(pattern, replace_func, value)
                adjusted_params[key] = adjusted_value
            else:
                adjusted_params[key] = value
        return adjusted_params
