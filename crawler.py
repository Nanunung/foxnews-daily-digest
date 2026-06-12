import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

def parse_foxnews_html(html, section_name):
    """Parses Fox News section HTML to extract articles."""
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    
    # Try selecting via article containers first
    article_elements = soup.select('article.article, .article-list article, [class*="article-list"] article, .list-simple article')
    
    for el in article_elements:
        title_el = el.select_one('.title a, h2.title a, h4.title a, h2 a, h4 a, a[href]')
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        url = title_el.get('href', '')
        if not title or not url:
            continue
            
        if url.startswith('/'):
            url = 'https://www.foxnews.com' + url
        elif not url.startswith('http'):
            continue
            
        # Try to find date/time
        date_el = el.select_one('.time, .date, [class*="time"], [class*="date"]')
        date_str = date_el.get_text(strip=True) if date_el else "N/A"
        
        # Avoid duplicates within this scrape
        if not any(a['url'] == url for a in articles):
            articles.append({
                'title': title,
                'url': url,
                'section': section_name,
                'date': date_str
            })
        
    # Fallback to direct title link search if list is empty/small
    if len(articles) < 5:
        title_links = soup.select('h2.title a, h4.title a, .info h2 a, .info h4 a, .content h2 a, .content h4 a')
        for link in title_links:
            title = link.get_text(strip=True)
            url = link.get('href', '')
            if not title or not url:
                continue
            if url.startswith('/'):
                url = 'https://www.foxnews.com' + url
            elif not url.startswith('http'):
                continue
                
            if any(a['url'] == url for a in articles):
                continue
                
            # Try to find relative date in parent elements
            parent = link.find_parent(['div', 'article', 'li'])
            date_str = "N/A"
            if parent:
                date_el = parent.select_one('.time, .date, [class*="time"], [class*="date"]')
                if date_el:
                    date_str = date_el.get_text(strip=True)
            
            articles.append({
                'title': title,
                'url': url,
                'section': section_name,
                'date': date_str
            })
            
    return articles

def fetch_section_static(url, section_name):
    """Attempts to crawl page statically using requests."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            articles = parse_foxnews_html(response.text, section_name)
            return articles
    except Exception as e:
        print(f"[Requests] Error crawling {url}: {e}")
    return []

def fetch_section_dynamic(url, section_name):
    """Fallback crawl using Playwright headless browser."""
    print(f"[Playwright] Falling back to headless browser for {url}...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS['User-Agent'])
            
            # Navigate and wait for content
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            # Wait for article tags or headings
            try:
                page.wait_for_selector('article, h2.title, h4.title', timeout=5000)
            except Exception:
                pass # Continue parsing even if timeout to see if anything is there
                
            html = page.content()
            browser.close()
            
            articles = parse_foxnews_html(html, section_name)
            return articles
    except Exception as e:
        print(f"[Playwright] Error crawling {url}: {e}")
    return []

def crawl_foxnews():
    """Crawls Politics, US, and World sections. Returns top 20 unique articles."""
    targets = [
        ('https://www.foxnews.com/politics', 'Politics'),
        ('https://www.foxnews.com/us', 'U.S.'),
        ('https://www.foxnews.com/world', 'World')
    ]
    
    all_articles = []
    seen_urls = set()
    
    for url, section in targets:
        print(f"Crawling {section} from {url}...")
        # Try static first
        articles = fetch_section_static(url, section)
        
        # If empty, fallback to dynamic
        if not articles:
            articles = fetch_section_dynamic(url, section)
            
        print(f"Collected {len(articles)} articles from {section}")
        
        for art in articles:
            # Deduplicate by URL
            if art['url'] not in seen_urls:
                seen_urls.add(art['url'])
                all_articles.append(art)
                
        # Politeness delay
        time.sleep(1)
        
    # Filter to top 20 total articles (or limit if needed)
    top_articles = all_articles[:20]
    print(f"Total unique articles collected: {len(top_articles)}")
    return top_articles

if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    # Test execution
    res = crawl_foxnews()
    for idx, a in enumerate(res):
        print(f"{idx+1}. [{a['section']}] {a['title']} ({a['date']}) - {a['url']}")
