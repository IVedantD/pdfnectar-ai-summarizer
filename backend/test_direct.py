import os
import requests
import json
from dotenv import load_dotenv

def test_direct_request():
    load_dotenv(override=True)
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key or api_key == "YOUR_OPENROUTER_API_KEY":
        print("❌ OPENROUTER_API_KEY is not set.")
        return

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "PDFNectar"
    }
    
    data = {
        "model": "qwen/qwen3-next-80b-a3b-instruct:free",
        "messages": [
            {"role": "user", "content": "Hi"}
        ]
    }
    
    print(f"Testing direct request to {url}...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Direct request successful!")
        else:
            print("❌ Direct request failed.")
            
    except Exception as e:
        print(f"❌ Error during request: {str(e)}")

if __name__ == "__main__":
    test_direct_request()
