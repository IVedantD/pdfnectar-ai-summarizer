import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_openrouter():
    load_dotenv(override=True)
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-next-80b-a3b-instruct:free")
    site_url = os.getenv("SITE_URL", "http://localhost:3000")
    site_name = os.getenv("SITE_NAME", "PDFNectar")

    if not api_key or api_key == "YOUR_OPENROUTER_API_KEY":
        logger.error("❌ OPENROUTER_API_KEY is not set in .env. Please add your key first.")
        return

    logger.info(f"Testing OpenRouter with model: {model}")
    
    try:
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": site_url,
                "X-Title": site_name,
            },
            temperature=0.1,
        )
        
        response = llm.invoke("Hi, who are you and what model are you?")
        print("\n--- OpenRouter Response ---")
        print(response.content)
        print("---------------------------\n")
        logger.info("✅ OpenRouter connection successful!")
        
    except Exception as e:
        logger.error(f"❌ OpenRouter test failed: {str(e)}")

if __name__ == "__main__":
    test_openrouter()
