from gensphere_python_sdk.AgenticFlow.AgenticFlow import AgenticFlow
from gensphere_python_sdk.AgenticFlow.AgenticFlowThreading import AgenticFlowThreading
import networkx
from dotenv import load_dotenv

# Define dummy executor classes with a run method for demonstration
class AExecutor:
    def __init__(self):
        print("AExecutor initialized")

    def run(self):
        print("Running AExecutor")
        return "Output of A"

class BExecutor:
    def __init__(self, value):
        self.value = value
        print(f"BExecutor initialized with value: {value}")

    def run(self, input_a):
        print(f"Running BExecutor with {input_a} and value {self.value}")
        return f"Output of B with value {self.value}"

class CExecutor:
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2
        print(f"CExecutor initialized with args: {arg1}, {arg2}")

    def run(self, input_a, input_b):
        print(f"Running CExecutor with {input_a}, {input_b}, and args {self.arg1}, {self.arg2}")
        return f"Output of C with args {self.arg1}, {self.arg2}"

# Define the available classes
available_classes = {
    "AExecutor": AExecutor,
    "BExecutor": BExecutor,
    "CExecutor": CExecutor
}

# Initialize and run the GraphExecutor with the YAML file path
executor = AgenticFlow('task_dag.yml', available_classes,'aws_db_table')
executor_threading = AgenticFlowThreading('task_dag.yml', available_classes,'aws_db_table')

if __name__=='__main__':
    load_dotenv()
    executor.execute()
    print('now starting threading version')
    executor_threading.execute()