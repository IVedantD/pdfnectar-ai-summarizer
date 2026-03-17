from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()
os.environ['GOOGLE_API_KEY'] = os.environ.get('GEMINI_API_KEY')

models = [
    'gemini-1.5-flash', 
    'gemini-1.5-flash-latest', 
    'gemini-2.5-flash', 
    'models/gemini-1.5-flash', 
    'gemini-pro',
    'gemini-1.0-pro'
]
valid = []

for m in models:
    try:
        llm = ChatGoogleGenerativeAI(model=m)
        res = llm.invoke('hi')
        valid.append(m)
        print(f'SUCCESS: {m}')
    except Exception as e:
        pass
        # print(f'FAILED {m}: {str(e)}')

print(f'\nValid models: {valid}')
