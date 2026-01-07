"""Generate response template files from actual API responses."""

import json
import sys
from pathlib import Path

try:
    from test_integration import IntegrationTestRunner
except ImportError as e:
    print(f"Error importing test_integration: {e}")
    print("Please ensure test_integration.py is in the same directory")
    sys.exit(1)

def generate_responses(base_url: str = "http://localhost:8000"):
    """Generate response files from actual API calls."""
    runner = IntegrationTestRunner(base_url=base_url)
    requests_dir = Path(__file__).parent / "request_payloads"
    responses_dir = Path(__file__).parent / "responses"
    responses_dir.mkdir(exist_ok=True)
    
    request_files = list(requests_dir.glob("*.json"))
    
    print(f"Generating response templates for {len(request_files)} test cases...")
    print(f"Base URL: {base_url}\n")
    
    success_count = 0
    error_count = 0
    
    for request_file in request_files:
        test_name = request_file.stem
        print(f"Processing: {test_name}...", end=" ")
        
        try:
            request_data = runner.load_request(test_name)
            response = runner.make_request(request_data)
            
            if response.status_code == 200:
                response_data = response.json()
                response_file = responses_dir / f"{test_name}.json"
                
                with open(response_file, 'w') as f:
                    json.dump(response_data, f, indent=2, ensure_ascii=False)
                print(f"✓ Saved to {response_file.name}")
                success_count += 1
            else:
                print(f"✗ HTTP {response.status_code}: {response.text[:100]}")
                error_count += 1
        except Exception as e:
            print(f"✗ Error: {str(e)[:100]}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"Generation complete!")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    generate_responses(url)

