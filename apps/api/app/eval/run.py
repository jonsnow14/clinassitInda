import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Eval runner")
    parser.add_argument("--suite", type=str, choices=["unit_ops", "retrieval", "clinical", "full", "journeys"], help="Suite to run")
    parser.add_argument("--mode", type=str, choices=["unit", "replay", "live", "chroma"], default="unit", help="Mode to run in")
    parser.add_argument("--baseline", type=str, help="Path to baseline json")
    parser.add_argument("--case", type=str, help="Single case ID to run")
    parser.add_argument("--dump-notes", action="store_true", help="Dump worker notes to traces")
    parser.add_argument("--judge", type=str, choices=["none", "sarvam", "external"], default="none")
    parser.add_argument("--strict-judge", action="store_true", help="Treat judge timeout as critical fail")
    
    args = parser.parse_args()
    
    if args.suite == "unit_ops":
        print("Running unit_ops suite...")
        # Stub for ops tests running via pytest
        print("Use pytest -m unit to run ops_judge tests.")
        return 0
        
    print(f"Suite {args.suite} not implemented in skeleton.")
    return 2

if __name__ == "__main__":
    sys.exit(main())
