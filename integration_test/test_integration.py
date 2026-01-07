"""Integration tests for all Schema Transformer API actions."""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import requests
except ImportError:
    print("Error: 'requests' module not found.")
    print("Please install it using: pip install requests")
    print("Or activate the virtual environment: source ../venv/bin/activate")
    sys.exit(1)

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REQUESTS_DIR = Path(__file__).parent / "request_payloads"
RESPONSES_DIR = Path(__file__).parent / "responses"


class IntegrationTestRunner:
    """Runner for integration tests."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def load_request(self, test_name: str) -> Dict[str, Any]:
        """Load request payload from file."""
        request_file = REQUESTS_DIR / f"{test_name}.json"
        if not request_file.exists():
            raise FileNotFoundError(f"Request file not found: {request_file}")
        
        with open(request_file, 'r') as f:
            return json.load(f)
    
    def load_expected_response(self, test_name: str) -> Optional[Dict[str, Any]]:
        """Load expected response from file."""
        response_file = RESPONSES_DIR / f"{test_name}.json"
        if not response_file.exists():
            return None
        
        with open(response_file, 'r') as f:
            return json.load(f)
    
    def make_request(self, request_data: Dict[str, Any]) -> requests.Response:
        """Make HTTP request based on request data."""
        method = request_data.get("method", "GET").upper()
        endpoint = request_data.get("endpoint", "/")
        headers = request_data.get("headers", {})
        body = request_data.get("body")
        
        url = f"{self.base_url}{endpoint}"
        
        if method == "GET":
            return self.session.get(url, headers=headers, timeout=30)
        elif method == "POST":
            return self.session.post(url, json=body, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
    
    def compare_responses(self, actual: Dict[str, Any], expected: Dict[str, Any], path: str = "") -> List[str]:
        """Compare actual and expected responses, return list of differences."""
        differences = []
        
        if not isinstance(actual, type(expected)):
            differences.append(f"{path}: Type mismatch - expected {type(expected).__name__}, got {type(actual).__name__}")
            return differences
        
        if isinstance(expected, dict):
            for key, expected_value in expected.items():
                new_path = f"{path}.{key}" if path else key
                if key not in actual:
                    differences.append(f"{new_path}: Missing key in actual response")
                else:
                    differences.extend(self.compare_responses(actual[key], expected_value, new_path))
        
        elif isinstance(expected, list):
            if len(actual) != len(expected):
                differences.append(f"{path}: List length mismatch - expected {len(expected)}, got {len(actual)}")
            else:
                for i, (actual_item, expected_item) in enumerate(zip(actual, expected)):
                    differences.extend(self.compare_responses(actual_item, expected_item, f"{path}[{i}]"))
        
        else:
            if actual != expected:
                differences.append(f"{path}: Value mismatch - expected {expected}, got {actual}")
        
        return differences
    
    def run_test(self, test_name: str, strict: bool = False) -> Dict[str, Any]:
        """Run a single integration test."""
        print(f"\n{'='*60}")
        print(f"Running test: {test_name}")
        print(f"{'='*60}")
        
        try:
            request_data = self.load_request(test_name)
            print(f"✓ Loaded request from: {test_name}.json")
            
            response = self.make_request(request_data)
            print(f"✓ Made {request_data['method']} request to {request_data['endpoint']}")
            print(f"  Status Code: {response.status_code}")
            
            try:
                actual_response = response.json()
            except json.JSONDecodeError:
                actual_response = {"raw": response.text}
            
            expected_response = self.load_expected_response(test_name)
            
            result = {
                "test_name": test_name,
                "status": "PASSED",
                "status_code": response.status_code,
                "request": request_data,
                "actual_response": actual_response,
                "expected_response": expected_response,
                "differences": [],
                "error": None
            }
            
            if expected_response:
                print(f"✓ Loaded expected response from: {test_name}.json")
                differences = self.compare_responses(actual_response, expected_response)
                
                if differences:
                    result["differences"] = differences
                    if strict:
                        result["status"] = "FAILED"
                        print(f"✗ Test FAILED - Found {len(differences)} differences:")
                        for diff in differences[:10]:
                            print(f"  - {diff}")
                        if len(differences) > 10:
                            print(f"  ... and {len(differences) - 10} more")
                    else:
                        print(f"⚠ Test PASSED with {len(differences)} differences (non-strict mode)")
                        for diff in differences[:5]:
                            print(f"  - {diff}")
                else:
                    print(f"✓ Test PASSED - Response matches expected")
            else:
                print(f"⚠ No expected response file found - showing actual response:")
                print(json.dumps(actual_response, indent=2))
            
            if response.status_code >= 400:
                result["status"] = "FAILED"
                result["error"] = f"HTTP {response.status_code}: {response.text}"
                print(f"✗ Test FAILED - HTTP {response.status_code}")
            
            return result
            
        except Exception as e:
            error_result = {
                "test_name": test_name,
                "status": "ERROR",
                "error": str(e),
                "request": None,
                "actual_response": None,
                "expected_response": None
            }
            print(f"✗ Test ERROR: {str(e)}")
            return error_result
    
    def run_all_tests(self, strict: bool = False) -> Dict[str, Any]:
        """Run all integration tests."""
        print(f"\n{'#'*60}")
        print(f"# Integration Test Suite for Schema Transformer API")
        print(f"# Base URL: {self.base_url}")
        print(f"{'#'*60}")
        
        request_files = list(REQUESTS_DIR.glob("*.json"))
        test_names = sorted([f.stem for f in request_files])
        
        if not test_names:
            print("No test files found in requests/ directory")
            return {"tests": [], "summary": {}}
        
        print(f"\nFound {len(test_names)} test cases:")
        for name in test_names:
            print(f"  - {name}")
        
        results = []
        for test_name in test_names:
            result = self.run_test(test_name, strict=strict)
            results.append(result)
            self.results.append(result)
        
        summary = {
            "total": len(results),
            "passed": sum(1 for r in results if r["status"] == "PASSED"),
            "failed": sum(1 for r in results if r["status"] == "FAILED"),
            "errors": sum(1 for r in results if r["status"] == "ERROR")
        }
        
        print(f"\n{'#'*60}")
        print(f"# Test Summary")
        print(f"{'#'*60}")
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        print(f"{'#'*60}\n")
        
        return {
            "tests": results,
            "summary": summary
        }
    
    def save_results(self, output_file: str = "test_results.json"):
        """Save test results to file."""
        output_path = Path(__file__).parent / output_file
        with open(output_path, 'w') as f:
            json.dump({
                "tests": self.results,
                "summary": {
                    "total": len(self.results),
                    "passed": sum(1 for r in self.results if r["status"] == "PASSED"),
                    "failed": sum(1 for r in self.results if r["status"] == "FAILED"),
                    "errors": sum(1 for r in self.results if r["status"] == "ERROR")
                }
            }, f, indent=2)
        print(f"✓ Results saved to {output_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run integration tests for Schema Transformer API")
    parser.add_argument("--url", default=BASE_URL, help="Base URL for API")
    parser.add_argument("--strict", action="store_true", help="Strict mode - fail on any differences")
    parser.add_argument("--test", help="Run specific test only")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    
    args = parser.parse_args()
    
    runner = IntegrationTestRunner(base_url=args.url)
    
    if args.test:
        result = runner.run_test(args.test, strict=args.strict)
        print(f"\nTest Status: {result['status']}")
    else:
        results = runner.run_all_tests(strict=args.strict)
        if args.save:
            runner.save_results()
        
        # Exit with error code if any tests failed
        if results["summary"]["failed"] > 0 or results["summary"]["errors"] > 0:
            sys.exit(1)

