# graph_builder.py

import yaml
import os

def parse_yaml(yaml_file):
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    return data

def build_graph_data(yaml_file):
    data = parse_yaml(yaml_file)
    elements = []
    node_ids = set()
    edges = []

    def add_nodes(nodes, parent_id=None, prefix=''):
        for node in nodes:
            node_name = node['name']
            node_id = prefix + node_name
            if node_id not in node_ids:
                node_ids.add(node_id)
                # Add node element
                elements.append({
                    'data': {
                        'id': node_id,
                        'label': node_name,  # Use original name for label
                        'type': node.get('type'),
                        'function': node.get('function'),
                        'function_call': node.get('function_call'),
                    },
                    'classes': node.get('type')
                })
                # Add edge from parent to current node
                if parent_id:
                    edge = {
                        'data': {'source': parent_id, 'target': node_id},
                        'classes': 'parent-edge'
                    }
                    edges.append(edge)
            # Add edges based on dependencies
            if 'params' in node:
                for param_value in node['params'].values():
                    if isinstance(param_value, str) and '{{' in param_value:
                        # Extract the node name from the template
                        template = param_value.strip('{} ').strip()
                        dep_node_name = template.split('.')[0]
                        dep_node_id = prefix + dep_node_name
                        # Only add the edge if the source node exists
                        if dep_node_id in node_ids:
                            edge = {
                                'data': {'source': dep_node_id, 'target': node_id},
                                'classes': 'dependency-edge'
                            }
                            edges.append(edge)
            # Recursively handle subflows
            if node.get('type') == 'yml_flow':
                sub_yaml_file = node['yml_file']
                if os.path.exists(sub_yaml_file):
                    sub_data = parse_yaml(sub_yaml_file)
                    sub_nodes = sub_data.get('nodes', [])
                    # Add a node representing the subflow
                    subflow_node_id = node_id + '_subflow'
                    elements.append({
                        'data': {
                            'id': subflow_node_id,
                            'label': node_name + ' Subflow',
                            'type': 'subflow',
                        },
                        'classes': 'subflow-node'
                    })
                    # Add edge to subflow node
                    edge = {
                        'data': {'source': node_id, 'target': subflow_node_id},
                        'classes': 'subflow-edge'
                    }
                    edges.append(edge)
                    # Recursively add subflow nodes with updated prefix
                    add_nodes(sub_nodes, parent_id=subflow_node_id, prefix=subflow_node_id + '__')

    nodes = data.get('nodes', [])
    add_nodes(nodes)

    # Now that we have all nodes and edges, identify entrypoints and output nodes
    incoming_edges = {}
    outgoing_edges = {}

    for node in node_ids:
        incoming_edges[node] = 0
        outgoing_edges[node] = 0

    for edge in edges:
        source = edge['data']['source']
        target = edge['data']['target']
        if source in outgoing_edges:
            outgoing_edges[source] +=1
        else:
            outgoing_edges[source] = 1
        if target in incoming_edges:
            incoming_edges[target] +=1
        else:
            incoming_edges[target] = 1

    # Now, mark entrypoints and outputs
    for element in elements:
        node_id = element['data']['id']
        if incoming_edges.get(node_id, 0) == 0:
            # This is an entrypoint node
            if 'classes' in element:
                element['classes'] += ' entrypoint-node'
            else:
                element['classes'] = 'entrypoint-node'
        if outgoing_edges.get(node_id, 0) == 0:
            # This is an output node
            if 'classes' in element:
                element['classes'] += ' output-node'
            else:
                element['classes'] = 'output-node'

    elements.extend(edges)
    return elements
