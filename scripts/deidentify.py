"""
De-identification script for the keep-asking conversational nudge study.

Takes the raw study database (keep-asking.db) and an equity flags CSV from
Curtin SIMS, produces a research database (research.db) with:
  - Equity flags merged into sessions
  - All transcript turns preserved
  - NO student numbers anywhere

Workflow:
  1. Copy keep-asking.db from the VPS:
       scp user@vps:~/keep-asking-app/data/keep-asking.db ./data/

  2. Obtain equity CSV from Curtin SIMS with columns:
       student_number, equity_flag_ses, equity_flag_firstinfamily

  3. Run this script:
       python scripts/deidentify.py \\
           --db data/keep-asking.db \\
           --roster data/equity_flags.csv \\
           --output data/research.db

  4. Verify research.db looks correct (spot-check sessions, equity flags)

  5. Delete keep-asking.db (and the copy on the VPS)

After step 5, there is no way to connect session codes back to student numbers.
"""

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def load_equity_csv(path: Path) -> dict[str, dict]:
    """Load equity flags CSV. Returns {student_number: {ses: 0/1, fif: 0/1}}."""
    flags = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)

        # Validate expected columns
        required = {"student_number", "equity_flag_ses", "equity_flag_firstinfamily"}
        if not required.issubset(set(reader.fieldnames or [])):
            missing = required - set(reader.fieldnames or [])
            print(f"ERROR: CSV missing columns: {missing}")
            print(f"Found columns: {reader.fieldnames}")
            sys.exit(1)

        for row in reader:
            flags[row["student_number"].strip()] = {
                "ses": int(row["equity_flag_ses"]),
                "fif": int(row["equity_flag_firstinfamily"]),
            }
    return flags


def build_research_db(source_path: Path, roster_path: Path, output_path: Path):
    """Build de-identified research database with equity flags."""

    if output_path.exists():
        print(f"ERROR: {output_path} already exists. Remove it first to avoid accidental overwrites.")
        sys.exit(1)

    # Load source database
    src = sqlite3.connect(str(source_path))
    src.row_factory = sqlite3.Row

    # Load equity flags
    equity = load_equity_csv(roster_path)

    # Load linkage table (student_number -> session_code)
    linkage_rows = src.execute("SELECT student_number, session_code FROM linkage").fetchall()
    linkage = {row["student_number"]: row["session_code"] for row in linkage_rows}

    if not linkage:
        print("WARNING: Linkage table is empty. Were student numbers already destroyed?")

    # Create output database
    out = sqlite3.connect(str(output_path))
    out.execute("PRAGMA journal_mode=WAL")
    out.execute("PRAGMA foreign_keys=ON")

    out.executescript("""
        CREATE TABLE sessions (
            session_code            TEXT PRIMARY KEY,
            condition               TEXT NOT NULL,
            is_test                 INTEGER NOT NULL DEFAULT 0,
            created_at              TEXT NOT NULL,
            equity_flag_ses         INTEGER,
            equity_flag_firstinfamily INTEGER
        );

        CREATE TABLE turns (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_code  TEXT NOT NULL REFERENCES sessions(session_code),
            turn_number   INTEGER NOT NULL,
            role          TEXT NOT NULL,
            content       TEXT NOT NULL,
            timestamp     TEXT NOT NULL,
            epoch         REAL NOT NULL
        );

        CREATE INDEX idx_turns_session ON turns(session_code);
    """)

    # Build reverse lookup: session_code -> student_number
    session_to_student = {sc: sn for sn, sc in linkage.items()}

    # Copy sessions with equity flags
    sessions = src.execute(
        "SELECT session_code, condition, is_test, created_at FROM sessions"
    ).fetchall()

    matched = 0
    unmatched = 0
    test_sessions = 0

    for s in sessions:
        code = s["session_code"]
        is_test = s["is_test"]

        if is_test:
            test_sessions += 1
            ses_flag = None
            fif_flag = None
        else:
            student_num = session_to_student.get(code)
            if student_num and student_num in equity:
                ses_flag = equity[student_num]["ses"]
                fif_flag = equity[student_num]["fif"]
                matched += 1
            else:
                ses_flag = None
                fif_flag = None
                unmatched += 1
                reason = "no linkage" if not student_num else "not in roster"
                print(f"  WARNING: Session {code} — {reason}")

        out.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)",
            (code, s["condition"], is_test, s["created_at"], ses_flag, fif_flag),
        )

    # Copy all turns (no student numbers in turns table)
    turns = src.execute(
        "SELECT session_code, turn_number, role, content, timestamp, epoch FROM turns"
    ).fetchall()

    out.executemany(
        "INSERT INTO turns (session_code, turn_number, role, content, timestamp, epoch) VALUES (?, ?, ?, ?, ?, ?)",
        [(t["session_code"], t["turn_number"], t["role"], t["content"], t["timestamp"], t["epoch"]) for t in turns],
    )

    out.commit()

    # Verify: no student numbers in output
    out_tables = out.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = [t[0] for t in out_tables]
    if "linkage" in table_names:
        print("ERROR: linkage table found in output database!")
        sys.exit(1)

    # Summary
    print()
    print("=== De-identification complete ===")
    print(f"Source:          {source_path}")
    print(f"Roster:          {roster_path}")
    print(f"Output:          {output_path}")
    print(f"Sessions:        {len(sessions)} total")
    print(f"  Matched:       {matched}")
    print(f"  Unmatched:     {unmatched}")
    print(f"  Test:          {test_sessions} (excluded from matching)")
    print(f"Turns copied:    {len(turns)}")
    print(f"Timestamp:       {datetime.utcnow().isoformat()}")
    print()
    if unmatched:
        print(f"WARNING: {unmatched} non-test sessions could not be matched to equity flags.")
        print("Check warnings above for details.")
    print()
    print("NEXT STEPS:")
    print(f"  1. Spot-check research.db: sqlite3 {output_path} 'SELECT * FROM sessions LIMIT 5;'")
    print(f"  2. Delete source: rm {source_path}")
    print("  3. Delete keep-asking.db on the VPS")
    print("  4. Linkage is gone — de-identification is irreversible")

    src.close()
    out.close()


def main():
    parser = argparse.ArgumentParser(
        description="De-identify keep-asking study data and merge equity flags."
    )
    parser.add_argument(
        "--db", required=True, type=Path,
        help="Path to keep-asking.db (source database from VPS)",
    )
    parser.add_argument(
        "--roster", required=True, type=Path,
        help="Path to equity flags CSV (student_number, equity_flag_ses, equity_flag_firstinfamily)",
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        help="Path for output research.db (must not already exist)",
    )
    args = parser.parse_args()

    if not args.db.exists():
        print(f"ERROR: Source database not found: {args.db}")
        sys.exit(1)
    if not args.roster.exists():
        print(f"ERROR: Roster CSV not found: {args.roster}")
        sys.exit(1)

    build_research_db(args.db, args.roster, args.output)


if __name__ == "__main__":
    main()
