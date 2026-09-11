import subprocess
import sys
import os

# Python files to execute, in the exact order you want
FILES = [
    "scrapping/idp_scraping/idp_scraper.py",
    "scrapping/cdf_dataset_scrapping/cdf_comm_projects_scraper.py",
    "scrapping/cdf_dataset_scrapping/cdf_skill_dev_applicants_scraper.py",
    "scrapping/budget_scraper/budget_scraper.py",
]


def run_files():
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

    print("\nALL FILES EXECUTED SUCCESSFULLY.")


if __name__ == "__main__":
    run_files()