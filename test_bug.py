import sys
import os

print("Python is running...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# Test if file exists
if os.path.exists("flight_search_automation.py"):
    print("Script file exists")
else:
    print("Script file NOT found")

# Test imports
try:
    from playwright.sync_api import sync_playwright
    print("Playwright imported successfully")
except ImportError as e:
    print(f"Playwright import failed: {e}")

try:
    import json
    print("JSON imported successfully")
except ImportError as e:
    print(f"JSON import failed: {e}")

print("Test completed")