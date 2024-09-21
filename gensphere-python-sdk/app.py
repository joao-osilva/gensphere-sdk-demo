# app.py

import dash
from dash import html, dcc, Input, Output, State
import dash_cytoscape as cyto
import os
import yaml
import graph_builder
import inspect
import functions  # Your functions.py
import structured_output_schema  # Your functions_schema.py

app = dash.Dash(__name__)
server = app.server

# Load the stylesheet for styling the graph
default_stylesheet = [
    {'selector': 'node',
     'style': {
         'label': 'data(label)',
         'width': '60px',
         'height': '60px',
         'font-size': '12px',
         'background-color': '#888',
         'color': '#fff',
         'text-valign': 'center',
         'text-halign': 'center',
     }},
    {'selector': '.function_call',
     'style': {'background-color': '#0074D9'}},
    {'selector': '.llm_service',
     'style': {'background-color': '#2ECC40'}},
    {'selector': '.yml_flow',
     'style': {'background-color': '#FF851B'}},
    {'selector': '.subflow-node',
     'style': {'background-color': '#FFDC00'}},
    {'selector': '.entrypoint-node',
     'style': {'shape': 'diamond', 'border-width': '2px', 'border-color': '#fff'}},
    {'selector': '.output-node',
     'style': {'shape': 'star', 'border-width': '2px', 'border-color': '#fff'}},
    {'selector': 'edge',
     'style': {
         'curve-style': 'bezier',
         'target-arrow-shape': 'vee',
         'target-arrow-color': '#fff',
         'arrow-scale': 2,
         'width': 2,
         'line-color': '#ccc',
     }},
    {'selector': '.dependency-edge',
     'style': {'line-color': '#FF4136'}},
    {'selector': '.parent-edge',
     'style': {'line-color': '#7FDBFF'}},
    {'selector': '.subflow-edge',
     'style': {'line-style': 'dashed', 'line-color': '#FFDC00'}},
]

# Build the initial graph elements
yaml_file = 'combined.yaml'  # Replace with your composed YAML file
elements = graph_builder.build_graph_data(yaml_file)

app.layout = html.Div([
    html.H1('GenFlow Workflow Visualizer', style={'color': '#fff'}),
    html.Div([
        html.Label('YAML File Path:', style={'color': '#fff'}),
        dcc.Input(id='yaml-file-input', value=yaml_file, type='text', style={'width': '300px'}),
        html.Button('Load', id='load-button', n_clicks=0),
    ], style={'margin-bottom': '20px'}),
    cyto.Cytoscape(
        id='cytoscape',
        elements=elements,
        layout={'name': 'breadthfirst'},
        style={'width': '100%', 'height': '600px', 'border': '1px solid black', 'background-color': '#1e1e1e'},
        stylesheet=default_stylesheet,
    ),
    html.Div(id='node-data', style={'margin-top': '20px', 'whiteSpace': 'pre-wrap', 'color': '#fff'})
], style={'backgroundColor': '#2e2e2e', 'padding': '20px'})


# Callback to update the graph when a new YAML file is loaded or subflow is toggled
@app.callback(
    Output('cytoscape', 'elements'),
    [Input('load-button', 'n_clicks'),
     Input('cytoscape', 'tapNodeData')],
    [State('yaml-file-input', 'value'),
     State('cytoscape', 'elements')]
)
def update_graph(n_clicks, tapNodeData, yaml_file, elements):
    ctx = dash.callback_context

    if not ctx.triggered:
        # No trigger, return the current elements
        return elements
    else:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'load-button':
        # Load new YAML file
        if os.path.exists(yaml_file):
            elements = graph_builder.build_graph_data(yaml_file)
            return elements
        else:
            return []
    elif trigger_id == 'cytoscape':
        # Node was clicked
        data = tapNodeData
        if data and data.get('type') == 'yml_flow':
            node_id = data['id']
            # Check if subflow nodes are already in the elements
            subflow_prefix = node_id + '_subflow__'
            subflow_nodes = [elem for elem in elements if elem['data']['id'].startswith(subflow_prefix)]
            if subflow_nodes:
                # Subflow is expanded, so collapse it
                elements = [elem for elem in elements if not elem['data']['id'].startswith(subflow_prefix)]
                # Also remove the subflow node
                elements = [elem for elem in elements if elem['data']['id'] != node_id + '_subflow']
            else:
                # Subflow is collapsed, so expand it
                # Build subflow elements
                full_elements = graph_builder.build_graph_data(yaml_file)
                # Find the subflow elements
                new_elements = [elem for elem in full_elements if elem['data']['id'].startswith(subflow_prefix)]
                # Also include the subflow node and edge
                subflow_node_id = node_id + '_subflow'
                subflow_elements = [elem for elem in full_elements if elem['data']['id'] == subflow_node_id or
                                    (elem['data'].get('source') == node_id and elem['data'].get(
                                        'target') == subflow_node_id)]
                elements.extend(subflow_elements)
                elements.extend(new_elements)
            return elements
        else:
            return elements
    else:
        return elements


# Callback to display node information
@app.callback(
    Output('node-data', 'children'),
    Input('cytoscape', 'tapNodeData')
)
def display_node_data(data):
    if data:
        node_id = data['id']
        node_type = data.get('type', 'N/A')
        content = [html.H4(f"Node: {data['label']}", style={'color': '#fff'}),
                   html.P(f"Type: {node_type}", style={'color': '#fff'})]

        # Get function source code
        func_name = data.get('function')
        if func_name:
            func = getattr(functions, func_name, None)
            if func:
                source = inspect.getsource(func)
                content.append(html.H5(f"Function: {func_name}", style={'color': '#fff'}))
                content.append(html.Pre(source, style={'color': '#fff'}))

        # Get schema source code
        function_call = data.get('function_call')
        if function_call:
            schema_name = function_call.get('name')
            schema = getattr(function_schemas, schema_name, None)
            if schema:
                schema_source = inspect.getsource(schema)
                content.append(html.H5(f"Schema: {schema_name}", style={'color': '#fff'}))
                content.append(html.Pre(schema_source, style={'color': '#fff'}))

        return content
    return "Click on a node to see details."


if __name__ == '__main__':
    app.run_server(debug=True)
