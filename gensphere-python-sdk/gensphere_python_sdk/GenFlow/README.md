# GenFlow

**GenFlow** is a powerful, low-level framework designed for AI developers who want to build, share, and observe complex LLM-driven workflows with ease. With YAML-defined nodes and flows, GenFlow enables developers to create modular, composable, and portable AI workflows that integrate seamlessly with existing tools and libraries.

---

## Why GenFlow?

GenFlow is built to address three primary needs for AI developers:

### 1. Composability

Building complex LLM workflows has never been easier. Define each step of your workflow in YAML, and GenFlow will handle dependency resolution and node orchestration automatically. Reference outputs from other nodes with a simple, intuitive syntax, allowing for highly modular and reusable code.

### 2. Portability

Share your workflows effortlessly. With GenFlow, all you need to share is a set of YAML files and associated functions. Whether you’re collaborating with your team or sharing with the wider community, GenFlow ensures your workflows are easy to distribute and reproduce.

### 3. Observability

Gain complete control over your workflow execution. As a low-level framework, GenFlow allows developers to observe and debug their workflows in granular detail, ensuring that you understand every step of your LLM's decision-making process.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quickstart Guide](#quickstart-guide)
- [Examples](#examples)
- [Integrations](#integrations)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **YAML-defined Workflows**: Create complex execution graphs using simple YAML files.
- **Modular Design**: Easily extend functionalities by adding custom functions and sub-flows.
- **LLM Integration**: Seamlessly integrate with OpenAI's GPT models for advanced language tasks.
- **API Integrations**: Utilize APIs like Tavily and Spider for web search and data scraping.
- **Interoperable**: Compatible with other agent frameworks like AutoGen and Crews by exposing code as functions.

---

## Installation

```bash
pip install genflow
````
---

## Quickstart guide

### 1. Define Your Workflow in YAML
Create a sample `sample.yaml`

```yaml
# sample.yaml

nodes:
  - name: read_csv
    type: function_call
    function: read_csv_file
    params:
      file_path: "data.csv"
    outputs:
      - data

  - name: process_data
    type: function_call
    function: process_csv_data
    params:
      data: "{{ read_csv.data }}"
    outputs:
      - processed_data

  - name: analyze_data
    type: llm_service
    service: openai
    model: "gpt-4"
    function_call:
      name: AnalyzeDataFunction
    params:
      prompt: "{{ process_data.processed_data }}"
    outputs:
      - analysis_result

```
### 2. Create a Sub-Flow with a separate YAML file
Create a `data_processing_flow.yaml` file

```yaml
# data_processing_flow.yaml

nodes:
  - name: clean_data
    type: function_call
    function: clean_data_function
    params:
      data: "{{ data }}"
    outputs:
      - cleaned_data

  - name: analyze_cleaned_data
    type: llm_service
    service: openai
    model: "gpt-4"
    function_call:
      name: AnalyzeCleanedDataFunction
    params:
      cleaned_data: "{{ clean_data.cleaned_data }}"
    outputs:
      - cleaned_analysis

```
### 3. Use `yml_compose` to compose flows
Create a `compose_flows.py` file:

```python
# compose_flows.py

from genflow import YmlCompose

# Combine the main flow with the sub-flow
composer = YmlCompose(
    base_flow='sample.yaml',
    sub_flows={'data_processing': 'data_processing_flow.yaml'}
)

# Save the combined flow to a new file
composer.compose(output_file='combined_flow.yaml')

```

### 4. Implement your functions
Create  a `functions.py` file

```python
# functions.py

import pandas as pd

def read_csv_file(file_path):
    data = pd.read_csv(file_path)
    return {'data': data}

def process_csv_data(data):
    # Process your data here
    processed_data = data.describe().to_string()
    return {'processed_data': processed_data}

def clean_data_function(data):
    # Clean your data here
    cleaned_data = data.dropna()
    return {'cleaned_data': cleaned_data}
```
### 5. Run the Combined Workflow
Create a `main.py` file

```python
# main.py

from genflow import GenFlow

if __name__ == '__main__':
    # Load the combined flow
    flow = GenFlow.from_yaml('combined_flow.yaml')
    flow.run()
    print(flow.outputs)
```

### 6. Execute

``bash
python compose_flows.py
python main.py
``
This sequence will first combine `sample.yaml` and `data_processing_flow.yaml` into a single flow (combined_flow.yaml) and then run it.
---
## Examples

[coming soon]

---
## Integrations

### Using Other Agent Frameworks

GenFlow is designed to be interoperable with other agent-building frameworks like AutoGen and Crews. You can integrate these frameworks by exposing their functionalities as functions that can be called within GenFlow nodes.

**Example**:
```python
# functions.py

from autogen import SomeAutoGenFunction

def autogen_function_wrapper(input_data):
    result = SomeAutoGenFunction(input_data)
    return {'result': result}

```
By wrapping the functionality in a function, you can easily call it as a node within a GenFlow YAML-defined workflow.

---
## Contributing

We welcome contributions! Please read our contribution guidelines before making a pull request. Whether it's adding new features, improving documentation, or fixing bugs, we appreciate your help in making GenFlow better.

---
## License

This project is licensed under the MIT License - see the LICENSE file for details.