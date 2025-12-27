#!/usr/bin/env python3
"""
Daily AVENIR vesting release job runner

This script is designed to be run by cron (daily at 00:05 UTC).
It can also be executed manually for testing or replaying past dates.

Usage:
    # Daily run (default: today UTC)
    python -m scripts.run_avenir_vesting_release_job

    # Dry-run (simulation)
    python -m scripts.run_avenir_vesting_release_job --dry-run

    # Replay specific date
    python -m scripts.run_avenir_vesting_release_job --as-of 2025-01-27

    # Custom currency and max lots
    python -m scripts.run_avenir_vesting_release_job --currency USD --max-lots 500
"""

import argparse
import json
import sys
from datetime import date, datetime, timezone
from typing import Optional

# Add backend to path
sys.path.insert(0, '.')

from app.infrastructure.database import SessionLocal
from app.services.vesting_service import release_avenir_vesting_lots, VestingReleaseError


def generate_trace_id(as_of_date: date) -> str:
    """
    Generate a unique trace_id for the job run.
    
    Format: job-avenir-vesting-YYYYMMDD-<shortuuid>
    """
    from uuid import uuid4
    date_str = as_of_date.strftime('%Y%m%d')
    short_uuid = str(uuid4())[:8]  # First 8 chars of UUID
    return f"job-avenir-vesting-{date_str}-{short_uuid}"


def parse_as_of_date(as_of_str: Optional[str]) -> date:
    """
    Parse --as-of argument or default to today UTC.
    
    Args:
        as_of_str: Date string in YYYY-MM-DD format, or None
    
    Returns:
        date: UTC date
    """
    if as_of_str:
        try:
            return date.fromisoformat(as_of_str)
        except ValueError:
            raise ValueError(f"Invalid date format: {as_of_str}. Expected YYYY-MM-DD")
    else:
        # Default to today UTC
        return datetime.now(timezone.utc).date()


def main():
    """Main entry point for the job runner"""
    parser = argparse.ArgumentParser(
        description='Run AVENIR vesting release job',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--as-of',
        type=str,
        default=None,
        help='Date for maturity check (YYYY-MM-DD, default: today UTC)'
    )
    
    parser.add_argument(
        '--currency',
        type=str,
        default='AED',
        help='Currency filter (default: AED)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate without committing (default: false)'
    )
    
    parser.add_argument(
        '--max-lots',
        type=int,
        default=200,
        help='Maximum lots to process in one run (default: 200)'
    )
    
    args = parser.parse_args()
    
    # Parse as_of_date
    try:
        as_of_date = parse_as_of_date(args.as_of)
    except ValueError as e:
        print(json.dumps({
            "job": "avenir_vesting_release",
            "error": str(e),
            "exit_code": 1
        }), file=sys.stderr)
        sys.exit(1)
    
    # Generate trace_id
    trace_id = generate_trace_id(as_of_date)
    
    # Initialize DB session
    db = SessionLocal()
    
    try:
        # Run release job
        summary = release_avenir_vesting_lots(
            db=db,
            as_of_date=as_of_date,
            currency=args.currency.upper(),
            dry_run=args.dry_run,
            trace_id=trace_id,
            max_lots=args.max_lots,
        )
        
        # Prepare output JSON
        output = {
            "job": "avenir_vesting_release",
            "trace_id": trace_id,
            "as_of": as_of_date.isoformat(),
            "currency": args.currency.upper(),
            "dry_run": args.dry_run,
            "summary": summary,
            "exit_code": 0 if summary['errors_count'] == 0 else 1
        }
        
        # Print JSON to stdout (one line)
        print(json.dumps(output))
        
        # Exit with appropriate code
        sys.exit(output["exit_code"])
    
    except VestingReleaseError as e:
        error_output = {
            "job": "avenir_vesting_release",
            "trace_id": trace_id,
            "as_of": as_of_date.isoformat(),
            "currency": args.currency.upper(),
            "dry_run": args.dry_run,
            "error": str(e),
            "exit_code": 1
        }
        print(json.dumps(error_output), file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        error_output = {
            "job": "avenir_vesting_release",
            "trace_id": trace_id,
            "as_of": as_of_date.isoformat(),
            "currency": args.currency.upper(),
            "dry_run": args.dry_run,
            "error": f"Unexpected error: {type(e).__name__}: {str(e)}",
            "exit_code": 1
        }
        print(json.dumps(error_output), file=sys.stderr)
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == "__main__":
    main()

