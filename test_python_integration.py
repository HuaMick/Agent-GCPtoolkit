#!/usr/bin/env python3
"""Test script for Python API integration."""

from backend.services.secrets.src.workflows.secret_operations import get_secret

# Fetch the GEMINI_API_KEY secret
secret_value = get_secret("GEMINI_API_KEY", quiet=True)

# Print the retrieved value
print(secret_value)
