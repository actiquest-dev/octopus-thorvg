import subprocess
import json

# Получи token
token_output = subprocess.check_output([
    "gcloud", "auth", "application-default", "print-access-token"
]).decode().strip()

print(f"Token: {token_output[:20]}...")

import requests

response = requests.get(
    "https://us-central1-aiplatform.googleapis.com/v1/projects/gen-lang-client-0711067295/locations/us-central1/publishers/google/models",
    headers={"Authorization": f"Bearer {token_output}"}
)

models = response.json().get('models', [])
for model in models:
    name = model.get('displayName', 'N/A')
    if 'gemma' in name.lower() or 'flash' in name.lower():
        print(name)
