#!/usr/bin/env python3
"""Fetch three database secrets and construct PostgreSQL connection string."""

import subprocess
import sys


def get_secret(secret_name):
    """Fetch a secret using gcptoolkit CLI."""
    result = subprocess.run(
        ["gcptoolkit", "secrets", "get", "-q", secret_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error fetching {secret_name}: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def main():
    """Main function to fetch secrets and construct connection string."""
    db_host = get_secret("DB_HOST")
    db_user = get_secret("DB_USER")
    db_pass = get_secret("DB_PASS")

    connection_string = f"postgresql://{db_user}:{db_pass}@{db_host}/postgres"
    print(connection_string)


if __name__ == "__main__":
    main()
