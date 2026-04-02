"""Automated testing suite for the hybrid RAG system."""

import os
import subprocess
import json
import sys
from pathlib import Path

# Move to standard testing root directory if needed
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

CASES = [
    {
        "name": "Case 1: Local Knowledge Retrieval (Definition)",
        "query": "What is a Markov chain?",
        "expected_route": "local-led",
    },
    {
        "name": "Case 2: Local Knowledge Retrieval (Derivation)",
        "query": "Show me the derivation for the stationary distribution of a Markov chain.",
        "expected_route": "local-led",
    },
    {
        "name": "Case 3: Freshness / SOTA (Web-Led)",
        "query": "What is the latest state-of-the-art method for quantization-aware training in 2026?",
        "expected_route": "web-led",
    },
    {
        "name": "Case 4: Code / Context-Led",
        "query": "Why is my local_index.py script throwing an error?",
        "expected_route": "context-led",
    },
    {
        "name": "Case 5: Mixed / Broad Synthesis",
        "query": "Compare Markov chains with other stochastic processes.",
        "expected_route": "mixed",
    },
    {
        "name": "Case 6: Local Fallback on Missing Web Data",
        "query": "latest updates on quantum phase estimation bounds",
        "expected_route": "web-led",
        "expected_web_fallback": True
    }
]

def run_orchestrator(query: str) -> dict:
    """Run the orchestrator script and return JSON output."""
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "scripts", "orchestrate_research.py"),
        query,
        "--research-script",
        os.path.join(PROJECT_ROOT, "tests", "fake_research_harness.py")
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running orchestrator: {result.stderr}")
        return {}
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON output: {result.stdout}")
        return {}

def evaluate():
    """Run all test cases and print an evaluation report."""
    print("=" * 60)
    print("Hybrid RAG System Evaluation".center(60))
    print("=" * 60)
    
    passed_cases = 0
    
    for idx, case in enumerate(CASES, 1):
        print(f"\n[{idx}/6] Running {case['name']}...")
        print(f"  Query: '{case['query']}'")
        
        output = run_orchestrator(case["query"])
        
        if not output:
             print("  [FAIL] Failed to run orchestrator pipeline.")
             continue
             
        route = output.get("route", "")
        print(f"  Route: {route} (Expected: {case['expected_route']})")
        
        route_pass = route == case["expected_route"]
        
        if route_pass:
            print("  [PASS] Route classification correct.")
            passed_cases += 1
            
            # Additional checks based on route
            evidence = output.get("evidence_pack", {})
            local_count = evidence.get("local_count", 0)
            web_count = evidence.get("web_count", 0)
            
            print(f"  Evidence items: {local_count} local, {web_count} web.")
        else:
            print("  [FAIL] Route classification incorrect.")

    print("\n" + "=" * 60)
    print(f"Evaluation Complete: {passed_cases}/{len(CASES)} cases passed.")
    print("=" * 60)

if __name__ == "__main__":
    evaluate()
