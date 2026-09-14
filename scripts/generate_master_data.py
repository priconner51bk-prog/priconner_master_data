from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from master_data.pipeline import generate_from_upstream


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate shared Priconne master data")
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--unit-status", type=Path)
    args = parser.parse_args()
    result = generate_from_upstream(args.upstream, args.db, args.output,
                                    unit_status_path=args.unit_status)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
