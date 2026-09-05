import sys
import json
import importlib.util
from typing import List

# Define test cases for: Two Sum (target = num1 + num2)
TEST_CASES = [
    {"nums": [2, 7, 11, 15], "target": 9, "expected": [0, 1]},
    {"nums": [3, 2, 4], "target": 6, "expected": [1, 2]},
    {"nums": [3, 3], "target": 6, "expected": [0, 1]},
    {"nums": [-1, -2, -3, -4, -5], "target": -8, "expected": [2, 4]},
    {"nums": [1000000, 500, 1000, 2000000], "target": 3000000, "expected": [0, 3]},
]

def load_student_module(filepath="/mnt/student/solution.py"):
    spec = importlib.util.spec_from_file_location("student_solution", filepath)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load student solution from {filepath}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_tests():
    result = {
        "total_tests": len(TEST_CASES),
        "passed_tests": 0,
        "failed_tests": 0,
        "details": [],
        "verdict": "ACCEPTED"
    }

    try:
        student_module = load_student_module()
        if not hasattr(student_module, "two_sum"):
            result["verdict"] = "COMPILATION_ERROR"
            result["details"].append({"error": "Function 'two_sum(nums, target)' not found."})
            print(json.dumps(result))
            sys.exit(1)

        two_sum_fn = getattr(student_module, "two_sum")

        for idx, tc in enumerate(TEST_CASES, 1):
            nums = tc["nums"]
            target = tc["target"]
            expected = tc["expected"]
            try:
                actual = two_sum_fn(list(nums), target)
                # Sort indices for comparison
                if actual and sorted(actual) == sorted(expected):
                    result["passed_tests"] += 1
                    result["details"].append({"test": idx, "status": "PASSED"})
                else:
                    result["failed_tests"] += 1
                    result["details"].append({
                        "test": idx,
                        "status": "FAILED",
                        "expected": expected,
                        "actual": actual
                    })
                    result["verdict"] = "WRONG_ANSWER"
            except Exception as e:
                result["failed_tests"] += 1
                result["details"].append({
                    "test": idx,
                    "status": "RUNTIME_ERROR",
                    "error": str(e)
                })
                result["verdict"] = "RUNTIME_ERROR"

    except Exception as e:
        result["verdict"] = "EXECUTION_ERROR"
        result["details"].append({"error": str(e)})

    # Output machine-readable JSON result on stdout
    print(json.dumps(result))

if __name__ == "__main__":
    run_tests()
