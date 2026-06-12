import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables
load_dotenv()

def summarize_articles(articles):
    """Summarizes collected articles using Gemini API."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
        
    genai.configure(api_key=api_key)
    
    # Format the articles list into a readable prompt string
    articles_text = ""
    for idx, a in enumerate(articles):
        articles_text += f"{idx+1}. [{a['section']}] {a['title']} (URL: {a['url']})\n"
        
    prompt = f"""다음은 오늘 Fox News의 주요 기사입니다. 아래 형식으로 분석해주세요:
1. 오늘의 핵심 이슈 3가지 (각 2-3문장 요약)
2. 정치/사회/국제 섹션별 동향
3. 주목할 키워드 5개
4. 전반적인 논조 분석

---
[수집된 기사 목록]
{articles_text}
"""
    
    # Try using gemini-3.5-flash first, then fallback to other versions
    models_to_try = ['gemini-3.5-flash', 'gemini-3.1-flash-lite', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
    available_choices = []
    
    try:
        available_names = [m.name for m in genai.list_models()]
        for model_name in models_to_try:
            full_name = f"models/{model_name}"
            if full_name in available_names:
                available_choices.append(model_name)
        
        # Fallback to any model supporting generateContent if none of our preferences exist
        if not available_choices:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_choices.append(m.name.split('/')[-1])
                    break
    except Exception as e:
        print(f"Warning: Could not fetch models list: {e}")
        available_choices = models_to_try

    last_err = None
    for model_name in available_choices:
        try:
            print(f"Initializing model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            print("Requesting summary from Gemini API...")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error with model {model_name}: {e}")
            last_err = e
            
    raise last_err if last_err else Exception("No models found")

if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
        
    # Simple test with mock data
    mock_articles = [
        {"title": "Trump's push for $350 billion 'arsenal of freedom' hits GOP skepticism", "url": "https://example.com/1", "section": "Politics", "date": "N/A"},
        {"title": "Border Crisis: Migrant crossings rise in Texas", "url": "https://example.com/2", "section": "U.S.", "date": "N/A"},
        {"title": "Tensions rise in the Middle East after recent events", "url": "https://example.com/3", "section": "World", "date": "N/A"},
    ]
    try:
        res = summarize_articles(mock_articles)
        print("Gemini response:")
        print(res)
    except Exception as e:
        print(f"Error testing summarizer: {e}")
