import time
import sys
from crawler import crawl_foxnews
from summarizer import summarize_articles
from mailer import send_digest_email

def main():
    # Configure console encoding for Windows if supported
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
        
    start_time = time.time()
    print("==================================================")
    print("Starting Fox News Daily Digest Pipeline...")
    print("==================================================")
    
    # 1. Crawling
    try:
        articles = crawl_foxnews()
        if not articles:
            print("[ERROR] No articles were collected. Aborting pipeline.")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Crawling step failed: {e}")
        sys.exit(1)
        
    # 2. Summarization
    try:
        print("Starting article summarization...")
        summary = summarize_articles(articles)
        print("Summarization completed.")
    except Exception as e:
        print(f"[ERROR] Summarization step failed: {e}")
        sys.exit(1)
        
    # 3. Mailing
    try:
        print("Sending daily email report...")
        send_digest_email(summary, len(articles))
        print("Email sending step finished.")
    except Exception as e:
        print(f"[ERROR] Mailing step failed: {e}")
        sys.exit(1)
        
    end_time = time.time()
    runtime = end_time - start_time
    print("==================================================")
    print(f"Pipeline finished successfully in {runtime:.2f} seconds.")
    print("==================================================")

if __name__ == '__main__':
    main()
