import subprocess
import sys
import os

# Cleaning scripts to execute, in the exact order you want.
# NOTE: clean_administrative_wards_demographics.py MUST run before
# clean_health_facilities.py — the latter backfills its Constituency
# column from the former's cleaned output.
FILES = [
    "cleaning/clean_administrative_wards_demographics.py",
    "cleaning/clean_cdf_projects.py",
    "cleaning/clean_cdf_skills_applicants.py",
    "cleaning/clean_health_facilities.py",
    "cleaning/clean_master_capital_investment_framework.py",
    "cleaning/clean_ward_public_consultation_issues.py",
    "cleaning/clean_budget_revenue.py",
    "cleaning/clean_budget_raw_tables.py",
]


def run_files():
    os.makedirs(os.path.join("data", "clean"), exist_ok=True)

    for file in FILES:
        print("\n" + "=" * 70)
        print(f"RUNNING: {file}")
        print("=" * 70)

        if not os.path.exists(file):
            print(f"ERROR: File not found: {file}")
            print("Stopping execution.")
            sys.exit(1)

        result = subprocess.run(
            [sys.executable, file],
            check=False
        )

        if result.returncode != 0:
            print("\n" + "=" * 70)
            print(f"FAILED: {file}")
            print(f"Exit code: {result.returncode}")
            print("=" * 70)

            # Stop immediately if one script fails
            sys.exit(result.returncode)

        print("\n" + "=" * 70)
        print(f"COMPLETED: {file}")
        print("=" * 70)

    print("\nALL CLEANING SCRIPTS EXECUTED SUCCESSFULLY.")
    print("Clean datasets are in: data/clean/")


if __name__ == "__main__":
    run_files()
