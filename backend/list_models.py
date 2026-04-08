import requests

def get_free_models():
    response = requests.get("https://openrouter.ai/api/v1/models")
    if response.status_code == 200:
        models = response.json().get("data", [])
        free_models = [m for m in models if m.get("pricing", {}).get("prompt") == "0"]
        for m in free_models:
            print(f"- {m['id']} ({m.get('name', 'Unknown')})")
        print(f"\nTotal free models: {len(free_models)}")

if __name__ == "__main__":
    get_free_models()
