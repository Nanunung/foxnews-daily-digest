import os
import json
import base64
import re
from datetime import datetime
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Load env variables
load_dotenv()

def markdown_to_html(md_text):
    """Converts basic markdown elements to HTML styled for emails."""
    html = md_text
    
    # Split into lines and format headers and list items
    lines = html.split('\n')
    new_lines = []
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            new_lines.append('<br>')
            continue
            
        # 1. Convert numbering headings: "1. 오늘의 핵심 이슈 3가지"
        num_match = re.match(r'^(\d+)\.\s+(.*)$', line_strip)
        if num_match:
            num, content = num_match.groups()
            new_lines.append(
                f'<h3 style="color: #1a5276; margin-top: 25px; margin-bottom: 10px; font-size: 18px; border-left: 4px solid #2980b9; padding-left: 10px; font-weight: bold;">'
                f'{num}. {content}</h3>'
            )
            continue
            
        # 2. Convert bullet points: "- item" or "* item"
        list_match = re.match(r'^[\-\*]\s+(.*)$', line_strip)
        if list_match:
            content = list_match.group(1)
            new_lines.append(
                f'<li style="margin-left: 20px; margin-bottom: 8px; list-style-type: square; font-size: 14px; line-height: 1.6;">{content}</li>'
            )
            continue
            
        # 3. Convert markdown headers: "### Header"
        hash_match = re.match(r'^(\#+)\s+(.*)$', line_strip)
        if hash_match:
            hashes, content = hash_match.groups()
            level = min(len(hashes) + 1, 6)
            new_lines.append(
                f'<h{level} style="color: #2c3e50; margin-top: 20px; margin-bottom: 8px; font-weight: bold;">{content}</h{level}>'
            )
            continue
            
        # General line
        new_lines.append(line)
        
    html = '\n'.join(new_lines)
    
    # 4. Bold text: **text** -> <strong>text</strong>
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #1a5276;">\1</strong>', html)
    
    # 5. Link formatting: [text](url) -> <a href="url">text</a>
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" style="color: #2980b9; text-decoration: none; font-weight: bold;">\1</a>', html)
    
    return html

def get_credentials():
    """Gets valid credentials, either from env, local file, or OAuth flow."""
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    creds = None
    
    # Try Loading from GMAIL_TOKEN Environment Secret (Base64 encoded token.json)
    gmail_token_b64 = os.getenv("GMAIL_TOKEN")
    if gmail_token_b64:
        print("GMAIL_TOKEN environment variable found. Decoding token...")
        try:
            token_json = base64.b64decode(gmail_token_b64).decode('utf-8')
            token_info = json.loads(token_json)
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            print("Successfully loaded credentials from environment.")
        except Exception as e:
            print(f"Error initializing credentials from GMAIL_TOKEN env: {e}")
            
    # Try loading from local token.json
    if not creds and os.path.exists('token.json'):
        print("token.json found. Loading credentials...")
        try:
            with open('token.json', 'r') as token_file:
                creds = Credentials.from_authorized_user_info(json.load(token_file), SCOPES)
        except Exception as e:
            print(f"Error loading token.json: {e}")
            
    # If credentials do not exist or are invalid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Credentials expired. Refreshing...")
            try:
                creds.refresh(Request())
                with open('token.json', 'w') as token_file:
                    token_file.write(creds.to_json())
                print("Credentials refreshed and saved to token.json.")
            except Exception as e:
                print(f"Failed to refresh credentials: {e}")
                creds = None
                
        if not creds:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "credentials.json is missing! Please download your client secrets json "
                    "from Google Cloud Console, save it as credentials.json in the project root, and try again."
                )
            print("Initializing local browser-based OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.json', 'w') as token_file:
                token_file.write(creds.to_json())
            print("Credentials authorized and saved to token.json.")
            
    return creds

def send_digest_email(summary_text, article_count):
    """Formats and sends the Fox News Daily Digest email."""
    recipient = os.getenv("RECIPIENT_EMAIL")
    if not recipient:
        raise ValueError("RECIPIENT_EMAIL is not set in environment or .env file.")
        
    today_date = datetime.now().strftime("%Y/%m/%d")
    subject = f"[Fox News 요약] {today_date} 주요 뉴스"
    
    formatted_summary = markdown_to_html(summary_text)
    
    # HTML Layout with premium aesthetics
    html_body = f"""
    <html>
      <body style="margin: 0; padding: 20px; background-color: #f5f7fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <div style="max-width: 650px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e1e8ed; border-radius: 12px; padding: 30px; box-shadow: 0 4px 10px rgba(0,0,0,0.03);">
          
          <!-- Header -->
          <div style="border-bottom: 2px solid #2980b9; padding-bottom: 20px; margin-bottom: 25px;">
            <h1 style="color: #2c3e50; font-size: 22px; font-weight: bold; margin: 0 0 5px 0; text-transform: uppercase; letter-spacing: 0.5px;">
              Fox News Daily Digest
            </h1>
            <p style="color: #7f8c8d; font-size: 13px; margin: 0;">
              전송 일자: {today_date} | 분석된 기사: {article_count}개
            </p>
          </div>
          
          <!-- Content Body -->
          <div style="color: #2c3e50; font-size: 15px; line-height: 1.8;">
            {formatted_summary}
          </div>
          
          <!-- Footer -->
          <div style="margin-top: 40px; border-top: 1px solid #ecf0f1; padding-top: 20px; text-align: center; font-size: 11px; color: #bdc3c7;">
            본 메일은 Fox News Daily Digest 자동화 파이프라인을 통해 발송되었습니다.<br>
            © 2026 Fox News Digest pipeline. All rights reserved.
          </div>
          
        </div>
      </body>
    </html>
    """
    
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    
    # Construct MIME message
    message = MIMEMultipart()
    message['to'] = recipient
    message['subject'] = subject
    message.attach(MIMEText(html_body, 'html', 'utf-8'))
    
    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    print("Sending email via Gmail API...")
    send_result = service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()
    
    print(f"Email sent successfully. Message ID: {send_result.get('id')}")
    print("메일 발송 완료")
    return send_result

if __name__ == '__main__':
    # Test mail formatting (no send, print HTML)
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
        
    test_md = """
1. 오늘의 핵심 이슈 3가지
- **이슈 1**: 트럼프 대통령의 3500억 달러 규모 국방 예산안에 대해 공화당 내부에서도 회의적인 시각이 나오고 있습니다. [기사 보기](https://www.foxnews.com/politics/trumps-push-350-billion-arsenal-freedom-hits-gop-skepticism)
- **이슈 2**: 이란 테헤란 내부에서 혁명수비대(IRGC)의 폭정 하에 고통받는 주민들이 트럼프 대통령에게 현 기조를 유지해달라고 요청하고 있습니다.
- **이슈 3**: 델라웨어 소방관 소속 하원의원 후보가 전국 노조가 지지하는 친트럼프 정책에 반대해 비판을 받고 있습니다.

2. 정치/사회/국제 섹션별 동향
- **정치**: 국방비 증액 예산 협상과 노조 연계 소방관 정책을 둘러싼 여야 및 공화당 내 갈등이 고조되고 있습니다.
- **국제**: 이란 내부의 불만과 대미 협조 요청이 지속 보도되며 대외 긴장이 유지되고 있습니다.

3. 주목할 키워드 5개
**국방 예산**, **이란 혁명수비대**, **소방관 노조**, **트럼프**, **연방 예산**

4. 전반적인 논조 분석
트럼프 행정부의 정책적 정당성을 부각하면서도, 예산안과 연계하여 발생하는 의회 및 노조 내부의 갈등을 객관적이면서 보수적인 관점에서 분석하고 있습니다.
"""
    print("Formatted HTML preview:")
    print(markdown_to_html(test_md)[:1000] + "...")
