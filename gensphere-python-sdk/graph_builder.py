# graph_builder.py

import yaml
import os
import logging
from typing import Optional

# Configure module-level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Change to DEBUG for more detailed logs
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)


def parse_yaml(yaml_file: str) -> dict:
    """
    Parses a YAML file and returns its content.

    Args:
        yaml_file (str): Path to the YAML file.

    Returns:
        dict: Parsed YAML data.
    """
    if not os.path.exists(yaml_file):
        logger.error(f"YAML file '{yaml_file}' does not exist.")
        raise FileNotFoundError(f"YAML file '{yaml_file}' does not exist.")

    with open(yaml_file, 'r') as f:
        try:
            data = yaml.safe_load(f)
            logger.debug(f"Parsed YAML file '{yaml_file}': {data}")
            return data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file '{yaml_file}': {e}")
            raise


def extract_referenced_node(template_str: str) -> Optional[str]:
    """
    Extracts the referenced node name from a templated string.

    Args:
        template_str (str): The templated string, e.g., "{{ node.output }}".

    Returns:
        Optional[str]: The referenced node name or None if not found.
    """
    import re
    pattern = r"\{\{\s*([\w_]+)\.[\w_]+\s*\}\}"
    match = re.search(pattern, template_str)
    if match:
        return match.group(1)
    return None


def identify_and_style_entrypoints_outputs(elements: list) -> list:
    """
    Identifies entrypoint and output nodes based on incoming and outgoing edges and styles them accordingly.

    Args:
        elements (list): List of Cytoscape elements (nodes and edges).

    Returns:
        list: Updated list of Cytoscape elements with styled entrypoints and output nodes.
    """
    incoming_edges = {}
    outgoing_edges = {}

    # Initialize counts
    for elem in elements:
        if 'source' in elem['data'] and 'target' in elem['data']:
            source = elem['data']['source']
            target = elem['data']['target']
            outgoing_edges[source] = outgoing_edges.get(source, 0) + 1
            incoming_edges[target] = incoming_edges.get(target, 0) + 1

    # Iterate through nodes to identify entrypoints and outputs
    for elem in elements:
        if 'label' in elem['data']:
            node_id = elem['data']['id']
            node_type = elem['data'].get('type', '')
            # Check for entrypoint
            if incoming_edges.get(node_id, 0) == 0 and node_type != 'subflow-node':
                if 'classes' in elem:
                    elem['classes'] += ' entrypoint-node'
                else:
                    elem['classes'] = 'entrypoint-node'
                logger.debug(f"Marked node '{node_id}' as entrypoint.")
            # Check for output
            if outgoing_edges.get(node_id, 0) == 0 and node_type != 'subflow-node':
                if 'classes' in elem:
                    elem['classes'] += ' output-node'
                else:
                    elem['classes'] = 'output-node'
                logger.debug(f"Marked node '{node_id}' as output node.")

    return elements


def build_graph_data(yaml_file: str) -> list:
    """
    Builds graph data compatible with Cytoscape from a YAML workflow definition.

    Args:
        yaml_file (str): Path to the YAML file.

    Returns:
        list: List of Cytoscape elements (nodes and edges).
    """
    data = parse_yaml(yaml_file)
    elements = []
    node_ids = set()
    edges = []

    nodes = data.get('nodes', [])
    if not nodes:
        logger.warning(f"No nodes found in YAML file '{yaml_file}'.")
        return elements  # Return empty list if no nodes

    def add_nodes(nodes: list, parent_id: Optional[str] = None, prefix: str = ''):
        """
        Recursively adds nodes and edges to the Cytoscape elements list.

        Args:
            nodes (list): List of node dictionaries from YAML.
            parent_id (Optional[str]): ID of the parent node.
            prefix (str): Prefix to ensure unique node IDs in subflows.
        """
        for node in nodes:
            node_name = node.get('name')
            node_type = node.get('type')

            if not node_name:
                logger.error("A node without a 'name' was found.")
                raise ValueError("All nodes must have a 'name' field.")

            node_id = prefix + node_name

            if node_id in node_ids:
                logger.error(f"Duplicate node name '{node_id}' detected.")
                raise ValueError(f"Duplicate node name '{node_id}' detected.")

            node_ids.add(node_id)

            # Prepare node data with default fields to prevent null values
            node_data = {
                'id': node_id,
                'label': node_name,
                'type': node_type
            }

            # Include additional fields based on node type
            if node_type == 'function_call':
                node_data['function'] = node.get('function', '')
                node_data['function_call'] = node.get('function_call', '')
            elif node_type == 'llm_service':
                node_data['tools'] = node.get('tools', [])
                node_data['structured_output_schema'] = node.get('structured_output_schema', '')
            elif node_type in ['set_variable', 'get_variable']:
                node_data['variable_name'] = node.get('variable_name', '')
            elif node_type == 'get_variables':
                node_data['variables'] = node.get('variables', {})
            elif node_type == 'yml_flow':
                node_data['yml_file'] = node.get('yml_file', '')
            # Add other node types as needed

            # Add node element
            element = {
                'data': node_data,
                'classes': node_type  # Used for styling in Cytoscape
            }
            elements.append(element)
            logger.debug(f"Added node: {element}")

            # Add edge from parent to current node if parent exists
            if parent_id:
                edge = {
                    'data': {'source': parent_id, 'target': node_id},
                    'classes': 'parent-edge'  # Used for styling dependency edges
                }
                edges.append(edge)
                logger.debug(f"Added edge from '{parent_id}' to '{node_id}': {edge}")

            # Handle dependencies based on 'params' field
            if 'params' in node:
                for param_key, param_value in node['params'].items():
                    if isinstance(param_value, str) and '{{' in param_value and '}}' in param_value:
                        # Extract the referenced node name from the template {{ node.output }}
                        referenced_node = extract_referenced_node(param_value)
                        if referenced_node:
                            referenced_node_id = prefix + referenced_node
                            if referenced_node_id in node_ids:
                                dependency_edge = {
                                    'data': {'source': referenced_node_id, 'target': node_id},
                                    'classes': 'dependency-edge'  # Used for styling dependency edges
                                }
                                edges.append(dependency_edge)
                                logger.debug(f"Added dependency edge from '{referenced_node_id}' to '{node_id}': {dependency_edge}")
                            else:
                                logger.warning(f"Referenced node '{referenced_node_id}' not found for dependency in node '{node_id}'.")

            # Handle subflows recursively
            if node_type == 'yml_flow':
                sub_yaml_file = node.get('yml_file')
                if not sub_yaml_file:
                    logger.error(f"Node '{node_id}' of type 'yml_flow' must have a 'yml_file' field.")
                    raise ValueError(f"Node '{node_id}' of type 'yml_flow' must have a 'yml_file' field.")

                # Compute the absolute path of the sub-flow file
                sub_flow_file_path = os.path.join(os.path.dirname(yaml_file), sub_yaml_file)
                if not os.path.exists(sub_flow_file_path):
                    logger.error(f"Sub-flow YAML file '{sub_flow_file_path}' does not exist.")
                    raise FileNotFoundError(f"Sub-flow YAML file '{sub_flow_file_path}' does not exist.")

                logger.info(f"Processing sub-flow YAML file '{sub_flow_file_path}' for node '{node_id}'.")

                # Add a special node representing the subflow
                subflow_node_id = node_id + '__subflow'
                subflow_node = {
                    'data': {
                        'id': subflow_node_id,
                        'label': f"{node_name} Subflow",
                        'type': 'subflow-node'
                    },
                    'classes': 'subflow-node'
                }
                elements.append(subflow_node)
                node_ids.add(subflow_node_id)
                logger.debug(f"Added subflow node: {subflow_node}")

                # Add edge from the parent node to the subflow node
                subflow_edge = {
                    'data': {'source': node_id, 'target': subflow_node_id},
                    'classes': 'subflow-edge'  # Used for styling subflow edges
                }
                edges.append(subflow_edge)
                logger.debug(f"Added edge from '{node_id}' to '{subflow_node_id}': {subflow_edge}")

                # Parse the sub-flow YAML
                sub_flow_data = parse_yaml(sub_flow_file_path)
                sub_flow_nodes = sub_flow_data.get('nodes', [])
                if not sub_flow_nodes:
                    logger.warning(f"Sub-flow YAML file '{sub_flow_file_path}' contains no nodes.")
                    continue

                # Recursively add subflow nodes with updated prefix for unique IDs
                sub_prefix = subflow_node_id + '__'
                add_nodes(sub_flow_nodes, parent_id=subflow_node_id, prefix=sub_prefix)

    add_nodes(nodes)

    # Combine nodes and edges
    elements.extend(edges)

    # Identify and style entrypoints and output nodes
    elements = identify_and_style_entrypoints_outputs(elements)

    # Log the elements for debugging
    logger.info(f"Total elements generated: {len(elements)}")
    logger.debug(f"Elements: {elements}")

    return elements
