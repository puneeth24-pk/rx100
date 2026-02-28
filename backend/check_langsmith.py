import os
from dotenv import load_dotenv
from langsmith import Client

load_dotenv()
client = Client()

print("Checking LangSmith Traces for project:", os.getenv("LANGSMITH_PROJECT"))
try:
    runs = list(client.list_runs(project_name=os.getenv("LANGSMITH_PROJECT"), error=False, limit=5))
    print(f"Found {len(runs)} recent traces!")
    for run in runs:
        print(f" - [{run.run_type}] {run.name} | Status: {run.status} | ID: {run.id}")
except Exception as e:
    print(f"Error connecting to LangSmith: {e}")
