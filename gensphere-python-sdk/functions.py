# functions.py

import pandas as pd

def read_csv_file(file_path):
    """
    Reads a CSV file and returns the data.
    """
    try:
        data = pd.read_csv(file_path)
        print(f"Read CSV file from {file_path}")
        return {'data': data}
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        raise

def process_csv_data(data):
    """
    Processes the CSV data.
    """
    print("Processing CSV data")
    # Example processing: calculate mean of numeric columns
    processed_data = data.mean(numeric_only=True).to_dict()
    return {'processed_data': processed_data}

def format_analysis_request(processed_data):
    """
    Formats the processed data into a string for analysis.
    """
    print("Formatting analysis request")
    prompt = f"Please analyze the following data summary:\n{processed_data}"
    return {'analysis_prompt': prompt}
