# app.py

import dash
from dash import html, dcc, Input, Output, State
import dash_cytoscape as cyto
import os
import yaml
import graph_builder
import inspect
import functions  # Your functions.py
import structured_output_schema  # Your structured_output_schema.py
import logging

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for more detailed logs
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.hasHandlers():
    logger.addHandler(handler)

# Initialize Dash app
app = dash.Dash(__name__)
server = app.server

# Load the stylesheet for styling the graph
default_stylesheet = [
    {'selector': 'node',
     'style': {
         'label': 'data(label)',
         'width': '300px',
         'height': '300px',
         'font-size': '24px',
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
     'style': {
         'shape': 'rectangle',  # Changed from 'diamond' to 'rectangle'
         'border-width': '2px',
         'border-color': '#fff'
     }},
    {'selector': '.output-node',
     'style': {'shape': 'star', 'border-width': '2px', 'border-color': '#fff'}},
    {'selector': 'edge',
     'style': {
         'curve-style': 'bezier',
         'target-arrow-shape': 'vee',
         'target-arrow-color': '#fff',
         'arrow-scale': 2,
         'width': 2,
         'line-color': '#ccc',  # Uniform edge color
     }},
    # Removed specific edge types since all edges have the same color
    # {'selector': '.dependency-edge',
    #  'style': {'line-color': '#FF4136'}},
    # {'selector': '.parent-edge',
    #  'style': {'line-color': '#7FDBFF'}},
    # {'selector': '.subflow-edge',
    #  'style': {'line-style': 'dashed', 'line-color': '#FFDC00'}},
]

# Build the initial graph elements
yaml_file = 'combined.yaml'  # Replace with your composed YAML file
try:
    elements = graph_builder.build_graph_data(yaml_file)
except Exception as e:
    logger.error(f"Error building graph data: {e}")
    elements = []

# Log the elements
logger.info(f"Initial elements: {len(elements)}")
logger.debug(f"Elements: {elements}")

# Define the legend for the node types and shapes
legend = html.Div([
    html.H3('Legend', style={'color': '#fff', 'textAlign': 'center'}),
    html.Div([
        html.Div([
            html.Span(style={
                'display': 'inline-block',
                'width': '20px',
                'height': '20px',
                'backgroundColor': '#0074D9',
                'marginRight': '10px'
            }),
            html.Span('Function Call Node', style={'color': '#fff'})
        ], style={'marginBottom': '5px'}),
        html.Div([
            html.Span(style={
                'display': 'inline-block',
                'width': '20px',
                'height': '20px',
                'backgroundColor': '#2ECC40',
                'marginRight': '10px'
            }),
            html.Span('LLM Service Node', style={'color': '#fff'})
        ], style={'marginBottom': '5px'}),
        html.Div([
            html.Span(style={
                'display': 'inline-block',
                'width': '20px',
                'height': '20px',
                'backgroundColor': '#FF851B',
                'marginRight': '10px'
            }),
            html.Span('YAML Flow Node', style={'color': '#fff'})
        ], style={'marginBottom': '5px'}),
        html.Div([
            html.Span(style={
                'display': 'inline-block',
                'width': '20px',
                'height': '20px',
                'backgroundColor': '#FFDC00',
                'marginRight': '10px'
            }),
            html.Span('Subflow Node', style={'color': '#fff'})
        ], style={'marginBottom': '5px'}),
        html.Div([
            html.Span(style={
                'display': 'inline-block',
                'width': '20px',
                'height': '20px',
                'backgroundColor': '#888',
                'marginRight': '10px',
                'border': '2px solid #fff',
                'borderRadius': '50%'
            }),
            html.Span('Regular Node', style={'color': '#fff'})
        ], style={'marginBottom': '5px'}),
        html.Div([
            html.Span(style={
                'display': 'inline-block',
                'width': '20px',
                'height': '20px',
                'backgroundColor': '#0074D9',
                'marginRight': '10px',
                'border': '2px solid #fff',
                'borderRadius': '0%',  # Ensures rectangle shape
            }),
            html.Span('Entrypoint Node', style={'color': '#fff'})
        ], style={'marginBottom': '5px'}),
        html.Div([
            html.Span(style={
                'display': 'inline-block',
                'width': '20px',
                'height': '20px',
                'backgroundColor': '#0074D9',
                'marginRight': '10px',
                'border': '2px solid #fff',
                'clipPath': 'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)'
            }),
            html.Span('Output Node', style={'color': '#fff'})
        ], style={'marginBottom': '5px'}),
        # Removed edge color legends since all edges have the same color
    ], style={'padding': '10px'})
], style={
    'position': 'absolute',
    'bottom': '10px',
    'right': '10px',
    'backgroundColor': '#1e1e1e',
    'padding': '10px',
    'border': '1px solid #fff',
    'borderRadius': '5px',
    'width': '300px',
    'zIndex': '1000',  # Ensure legend is on top
    'color': '#fff'
})

# Define the layout
app.layout = html.Div([
    html.H1('GenFlow Workflow Visualizer', style={'color': '#fff'}),
    html.Div([
        html.Label('YAML File Path:', style={'color': '#fff'}),
        dcc.Input(id='yaml-file-input', value=yaml_file, type='text', style={'width': '300px'}),
        html.Button('Load', id='load-button', n_clicks=0, style={'marginLeft': '10px'}),
    ], style={'marginBottom': '20px'}),
    html.Div([
        cyto.Cytoscape(
            id='cytoscape',
            elements=elements if elements else [],
            layout={'name': 'breadthfirst'},
            style={'width': '100%', 'height': '600px', 'border': '1px solid black', 'background-color': '#1e1e1e'},
            stylesheet=default_stylesheet,
        ),
        legend,  # Add the legend here
    ], style={'position': 'relative'}),
    html.Div(id='node-data', style={'marginTop': '20px', 'whiteSpace': 'pre-wrap', 'color': '#fff'})
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
        logger.debug("No trigger for update_graph callback.")
        return dash.no_update
    else:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        logger.debug(f"Triggered by: {trigger_id}")

    if trigger_id == 'load-button':
        # Load new YAML file
        logger.debug(f"Load button clicked. Loading YAML file: {yaml_file}")
        if os.path.exists(yaml_file):
            try:
                elements = graph_builder.build_graph_data(yaml_file)
                logger.debug(f"Loaded elements: {elements}")
                return elements
            except Exception as e:
                # Log the error and return no update
                logger.error(f"Error loading YAML file '{yaml_file}': {e}")
                return dash.no_update
        else:
            logger.error(f"YAML file '{yaml_file}' does not exist.")
            return dash.no_update
    elif trigger_id == 'cytoscape':
        # Node was clicked
        data = tapNodeData
        logger.debug(f"Node clicked: {data}")
        if data and data.get('type') == 'yml_flow':
            node_id = data['id']
            # Check if subflow nodes are already in the elements
            subflow_prefix = node_id + '__'
            subflow_nodes = [elem for elem in elements if elem['data']['id'].startswith(subflow_prefix)]
            if subflow_nodes:
                # Subflow is expanded, so collapse it
                elements = [elem for elem in elements if not elem['data']['id'].startswith(subflow_prefix)]
                # Also remove the subflow node
                subflow_node_id = node_id + '__subflow'
                elements = [elem for elem in elements if elem['data']['id'] != subflow_node_id]
                logger.debug(f"Collapsed subflow for node '{node_id}'.")
            else:
                # Subflow is collapsed, so expand it
                try:
                    # Build subflow elements
                    full_elements = graph_builder.build_graph_data(yaml_file)
                    # Find the subflow elements
                    new_elements = [elem for elem in full_elements if elem['data']['id'].startswith(subflow_prefix)]
                    # Also include the subflow node and edge
                    subflow_node_id = node_id + '__subflow'
                    subflow_elements = [elem for elem in full_elements if elem['data']['id'] == subflow_node_id or
                                        (elem['data'].get('source') == node_id and elem['data'].get('target') == subflow_node_id)]
                    elements.extend(subflow_elements)
                    elements.extend(new_elements)
                    logger.debug(f"Expanded subflow for node '{node_id}'.")
                except Exception as e:
                    logger.error(f"Error expanding subflow for node '{node_id}': {e}")
                    return dash.no_update
            return elements
        else:
            # Not a yml_flow node, no need to update elements
            logger.debug("Clicked node is not a yml_flow type.")
            return dash.no_update
    else:
        logger.debug("No valid trigger found.")
        return dash.no_update

# Callback to display node information
@app.callback(
    Output('node-data', 'children'),
    Input('cytoscape', 'tapNodeData')
)
def display_node_data(data):
    if data:
        logger.debug(f"Displaying data for node: {data}")
        node_id = data.get('id', 'N/A')
        node_label = data.get('label', node_id)
        node_type = data.get('type', 'N/A')
        content = [
            html.H4(f"Node: {node_label}", style={'color': '#fff'}),
            html.P(f"Type: {node_type}", style={'color': '#fff'})
        ]

        if node_type == 'function_call':
            func_name = data.get('function', '')
            if func_name:
                func = getattr(functions, func_name, None)
                if func:
                    try:
                        source = inspect.getsource(func)
                        content.append(html.H5(f"Function: {func_name}", style={'color': '#fff'}))
                        content.append(html.Pre(source, style={'color': '#fff', 'backgroundColor': '#333', 'padding': '10px'}))
                    except OSError:
                        content.append(html.P(f"Source code for function '{func_name}' not available.", style={'color': '#fff'}))
                else:
                    content.append(html.P(f"Function '{func_name}' not found in 'functions.py'.", style={'color': '#fff'}))
            else:
                content.append(html.P("No function associated with this node.", style={'color': '#fff'}))

        elif node_type == 'llm_service':
            tools = data.get('tools', [])
            structured_output_schema_name = data.get('structured_output_schema', '')

            if tools:
                content.append(html.H5("Tools:", style={'color': '#fff'}))
                for tool_name in tools:
                    if not tool_name:
                        continue  # Skip empty tool names
                    func = getattr(functions, tool_name, None)
                    if func:
                        try:
                            source = inspect.getsource(func)
                            content.append(html.P(f"Function: {tool_name}", style={'color': '#fff'}))
                            content.append(html.Pre(source, style={'color': '#fff', 'backgroundColor': '#333', 'padding': '10px'}))
                        except OSError:
                            content.append(html.P(f"Source code for function '{tool_name}' not available.", style={'color': '#fff'}))
                    else:
                        content.append(html.P(f"Function '{tool_name}' not found in 'functions.py'.", style={'color': '#fff'}))

            if structured_output_schema_name:
                schema = getattr(structured_output_schema, structured_output_schema_name, None)
                if schema:
                    try:
                        source = inspect.getsource(schema)
                        content.append(html.H5(f"Structured Output Schema: {structured_output_schema_name}", style={'color': '#fff'}))
                        content.append(html.Pre(source, style={'color': '#fff', 'backgroundColor': '#333', 'padding': '10px'}))
                    except OSError:
                        content.append(html.P(f"Source code for schema '{structured_output_schema_name}' not available.", style={'color': '#fff'}))
                else:
                    content.append(html.P(f"Schema '{structured_output_schema_name}' not found in 'structured_output_schema.py'.", style={'color': '#fff'}))

        elif node_type == 'yml_flow':
            content.append(html.P("This node represents a sub-flow. Click to expand or collapse.", style={'color': '#fff'}))

        elif node_type == 'set_variable':
            variable_name = data.get('variable_name', 'N/A')
            value = data.get('value', 'N/A')
            content.append(html.P(f"Variable Name: {variable_name}", style={'color': '#fff'}))
            content.append(html.P(f"Value: {value}", style={'color': '#fff'}))

        elif node_type == 'get_variable':
            variable_name = data.get('variable_name', 'N/A')
            content.append(html.P(f"Variable Name: {variable_name}", style={'color': '#fff'}))

        elif node_type == 'get_variables':
            variables = data.get('variables', {})
            content.append(html.H5("Variables:", style={'color': '#fff'}))
            for output_name, variable_name in variables.items():
                content.append(html.P(f"{output_name}: {variable_name}", style={'color': '#fff'}))

        # Additional node types can be handled here

        return content
    else:
        logger.debug("No node data to display.")
    return "Click on a node to see details."

if __name__ == '__main__':
    app.run_server(debug=False)
