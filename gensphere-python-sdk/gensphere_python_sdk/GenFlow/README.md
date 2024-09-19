# GenFlow

**GenFlow** is a powerful, low-level framework designed for AI developers who want to build, share, and observe complex LLM-driven workflows with ease. With YAML-defined nodes and flows, AgenticFlow enables developers to create modular, composable, and portable AI workflows that integrate seamlessly with existing tools and libraries.

---

## Why AgenticFlow?

AgenticFlow is built to address three primary needs for AI developers:

### 1. Composability

Building complex LLM workflows has never been easier. Define each step of your workflow in YAML, and AgenticFlow will handle dependency resolution and node orchestration automatically. Reference outputs from other nodes with a simple, intuitive syntax, allowing for highly modular and reusable code.

### 2. Portability

Share your workflows effortlessly. With AgenticFlow, all you need to share is a set of YAML files and associated functions. Whether you’re collaborating with your team or sharing with the wider community, AgenticFlow ensures your workflows are easy to distribute and reproduce.

### 3. Observability

Gain complete control over your workflow execution. As a low-level framework, AgenticFlow allows developers to observe and debug their workflows in granular detail, ensuring that you understand every step of your LLM's decision-making process.

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
