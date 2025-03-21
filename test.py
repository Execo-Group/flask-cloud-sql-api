# test_env.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Print out the values
print(f"DB_USER: {os.environ.get('DB_USER')}")
print(f"DB_PASS: {'*' * len(os.environ.get('DB_PASS', ''))}") # Masked for security
print(f"DB_NAME: {os.environ.get('DB_NAME')}")
print(f"DB_HOST: {os.environ.get('DB_HOST')}")
print(f"DB_PORT: {os.environ.get('DB_PORT')}")