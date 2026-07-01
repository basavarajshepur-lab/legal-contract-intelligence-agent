"""
CLI runner for the Contract Intelligence Agent pipeline.

Usage:
  python run_pipeline.py --contract data/sample_contracts.json --id CONTRACT_001
  python run_pipeline.py --batch data/sample_contracts.json
"""

from dotenv import load_dotenv
load_dotenv()

import argparse
import json
import sys
from pathlib import Path
from core.models import Contract
from core.pipeline import process_contract


def print_result(result) -> None:
    assessment = result.risk_assessment
    print(f"\n{'='*60}")
    print(f"Contract ID : {result.contract_id}")
    print(f"Decision    : {assessment.decision.value}  (risk score: {assessment.risk_score}/100)")
    print(f"Confidence  : {assessment.confidence:.0%}  |  HITL required: {result.sent_to_hitl}")
    print(f"Audit ID    : {result.audit_id}")
    print(f"Processing  : {result.processing_time_ms:.0f}ms")
    print(f"\nKey deviations:")
    for dev in assessment.key_deviations:
        print(f"  - {dev}")
    print(f"\nReasoning:")
    for i, r in enumerate(assessment.reasoning, 1):
        print(f"  {i}. {r}")
    if result.redline_memo:
        print(f"\nRedline memo generated - {result.redline_memo.recommended_reviewer} review required before sending to counterparty")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Contract Intelligence Agent - multi-agent contract risk triage")
    parser.add_argument("--contract", required=True, help="Path to contracts JSON file")
    parser.add_argument("--id", dest="contract_id", help="Process specific contract by ID")
    parser.add_argument("--batch", action="store_true", help="Process all contracts in file")
    args = parser.parse_args()

    path = Path(args.contract)
    if not path.exists():
        print(f"Error: file not found: {path}")
        sys.exit(1)

    contracts_data = json.loads(path.read_text())

    if args.contract_id:
        contract_data = next((c for c in contracts_data if c["contract_id"] == args.contract_id), None)
        if not contract_data:
            print(f"Contract {args.contract_id} not found in file")
            sys.exit(1)
        contract = Contract(**contract_data)
        result = process_contract(contract)
        print_result(result)

    elif args.batch:
        print(f"\nProcessing {len(contracts_data)} contracts...\n")
        decisions = {"ACCEPT": 0, "FLAG": 0, "NEGOTIATE": 0, "REJECT": 0}
        for c in contracts_data:
            contract = Contract(**c)
            result = process_contract(contract)
            decisions[result.risk_assessment.decision.value] += 1
            print_result(result)
        print("\nBatch Summary:")
        for d, count in decisions.items():
            print(f"  {d}: {count}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
