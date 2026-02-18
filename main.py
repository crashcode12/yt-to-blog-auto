import os
import re
import yt_dlp
import requests
from google import genai

# הגדרת ה-Client של Gemini
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# סרטון הבדיקה שלנו (COMEX Silver Delivery Shock)
TEST_VIDEO_ID = "6vOKEkg7Uyg"
TEST_VIDEO_TITLE = "COMEX Silver Delivery Shock: What Happens in March?"
TEST_VIDEO_URL = f"https://www.youtube.com/watch?v={TEST_VIDEO_ID}"

def download_transcript(video_url):
    print("מפעיל את yt-dlp לשאיבת קובץ הכתוביות המקורי...")
    
    ydl_opts = {
        'skip_download': True, # אנחנו לא רוצים את הווידאו, רק את הטקסט
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'], # מבקש את הכתוביות באנגלית
        'subtitlesformat': 'vtt',
        'outtmpl': 'subtitle_%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # חיפוש קובץ הכתוביות שירד לשרת
        for file in os.listdir('.'):
            if file.startswith('subtitle_') and file.endswith('.vtt'):
                print("קובץ כתוביות ירד בהצלחה. מנקה את הטקסט...")
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                os.remove(file) # מחיקת הקובץ כדי לשמור על סדר
                
                # ניקוי הקובץ מזמנים ותגיות (משאיר רק את המילים באנגלית)
                text = re.sub(r'<[^>]+>', '', content)
                clean_lines = []
                for line in text.split('\n'):
                    if '-->' in line or line.strip().isdigit() or 'WEBVTT' in line or 'Kind:' in line or 'Language:' in line:
                        continue
                    if line.strip():
                        clean_lines.append(line.strip())
                
                # הסרת שורות כפולות (אופייני לכתוביות אוטומטיות)
                final_text = []
                for i, line in enumerate(clean_lines):
                    if i == 0 or line != clean_lines[i-1]:
                        final_text.append(line)
                
                return " ".join(final_text)
                
        print("לא נמצא קובץ כתוביות לאחר ההורדה.")
        return None
    except Exception as e:
        print(f"שגיאה ב-yt-dlp: {e}")
        return None

def process_with_gemini(title, text, url):
    print("הטקסט נמשך בהצלחה! מעביר ל-Gemini לתרגום וכתיבה...")
    prompt = f"כתוב כתבה כלכלית מקצועית בעברית עבור אתר 'Coinfolio' על בסיס התוכן הבא: {title}. תמלול: {text}. בסוף הוסף מקור: {url}"
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"שגיאה ב-AI: {e}")
        return None

def post_to_site(title, content):
    print("מנסה לפרסם לאתר...")
    api_url = f"{os.environ['SITE_URL']}/wp-json/wp/v2/posts"
    auth = (os.environ['SITE_USERNAME'], os.environ['SITE_PASSWORD'])
    data = {"title": title, "content": content, "status": "publish"}
    try:
        res = requests.post(api_url, json=data, auth=auth)
        return res.status_code
    except Exception as e:
        print(f"שגיאה בחיבור לאתר: {e}")
        return 500

if __name__ == "__main__":
    print("--- מתחיל בדיקה עם מנוע yt-dlp ---")
    
    text = download_transcript(TEST_VIDEO_URL)
    
    if text:
        article = process_with_gemini(TEST_VIDEO_TITLE, text, TEST_VIDEO_URL)
        if article:
            status = post_to_site(TEST_VIDEO_TITLE, article)
            if status in [200, 201]:
                print(f"הצלחה מסחררת! הכתבה פורסמה. סטטוס: {status}")
            else:
                print(f"הכתבה נכתבה אבל האתר החזיר שגיאה: {status}")
        else:
            print("הבדיקה נכשלה בשלב ה-AI.")
    else:
        print("הבדיקה נכשלה בשלב התמלול.")
