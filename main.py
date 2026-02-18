import os
import requests
import feedparser
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

CHANNELS = ["UCFddgboLcMQ4IUE681qvcqg"] # GoldCore TV
DB_FILE = "processed_videos.txt"

def get_processed_videos():
    if not os.path.exists(DB_FILE):
        return set()
    with open(DB_FILE, "r") as f:
        return set(f.read().splitlines())

def mark_as_processed(video_id):
    with open(DB_FILE, "a") as f:
        f.write(f"{video_id}\n")

def get_channel_feed(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return feedparser.parse(response.content) if response.status_code == 200 else None
    except:
        return None

def get_smart_transcript(video_id):
    """מנסה למשוך תמלול. יחזיר None אם יוטיוב חוסם את הבוט."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for transcript in transcript_list:
            if transcript.language_code == 'en':
                data = transcript.fetch()
                return " ".join([t['text'] for t in data])
        return None
    except:
        return None

def process_with_gemini(title, description, text, url):
    """
    כאן הקסם קורה: ג'מיני מקבל גם את התמלול וגם את התקציר מה-RSS.
    אם אין תמלול, הוא ישתמש בתקציר כדי לכתוב ידיעה קצרה.
    """
    print("מעביר ל-Gemini נתונים לעיבוד...")
    
    transcript_status = text if text else "התמלול המלא לא זמין עקב חסימת רשת, הסתמך על התיאור בלבד."
    
    prompt = f"""
    אתה עיתונאי כלכלי באתר 'Coinfolio'. עליך לכתוב כתבה בעברית על סרטון יוטיוב חדש.
    
    כותרת הסרטון: {title}
    תיאור הסרטון המקורי: {description}
    תמלול הסרטון: {transcript_status}
    
    הנחיות:
    1. אם יש תמלול ארוך, כתוב כתבת עומק מקיפה עם כותרות משנה.
    2. אם אין תמלול (כתוב שלא זמין), השתמש בכותרת ובתיאור המקורי כדי לכתוב "מבזק חדשות/תקציר" מקצועי בן פסקה או שתיים.
    3. תמיד הוסף בסוף: "לצפייה בסרטון המלא: {url}".
    """
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text
    except Exception as e:
        print(f"שגיאה ב-AI: {e}")
        return None

def post_to_site(title, content):
    api_url = f"{os.environ['SITE_URL']}/wp-json/wp/v2/posts"
    auth = (os.environ['SITE_USERNAME'], os.environ['SITE_PASSWORD'])
    data = {"title": title, "content": content, "status": "publish"}
    try:
        res = requests.post(api_url, json=data, auth=auth)
        return res.status_code
    except:
        return 500

if __name__ == "__main__":
    print("--- מתחיל ריצה אוטומטית (עם מנגנון גיבוי תיאור) ---")
    processed = get_processed_videos()
    
    for channel_id in CHANNELS:
        feed = get_channel_feed(channel_id)
        if not feed or not feed.entries:
            continue
            
        for entry in feed.entries:
            v_id = entry.yt_videoid
            
            if v_id in processed:
                continue
                
            print(f"\nבודק סרטון חדש: {entry.title}")
            
            # שולפים את התיאור המקורי מה-RSS!
            description = entry.summary if 'summary' in entry else "אין תיאור"
            
            # מנסים למשוך תמלול (אולי נצליח, אולי ניחסם)
            text = get_smart_transcript(v_id)
            if text:
                print("התמלול נמשך בהצלחה! מכין כתבת עומק.")
            else:
                print("התמלול נחסם על ידי יוטיוב. משתמש בתיאור הסרטון כגיבוי להכנת מבזק קצר.")
            
            # תמיד מייצרים כתבה!
            article = process_with_gemini(entry.title, description, text, entry.link)
            
            if article:
                status = post_to_site(entry.title, article)
                if status in [200, 201]:
                    print(f"הפוסט עלה לאתר! סטטוס: {status}")
                    mark_as_processed(v_id)
                    break 
                else:
                    print(f"שגיאה בפרסום לאתר: {status}")
            else:
                print("שגיאה ביצירת התוכן מ-Gemini.")
