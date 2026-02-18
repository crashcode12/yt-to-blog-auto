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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return feedparser.parse(response.content)
        else:
            print(f"שגיאת רשת ממשיכת RSS: קוד {response.status_code}", flush=True)
            return None
    except Exception as e:
        print(f"שגיאת חיבור ל-RSS: {e}", flush=True)
        return None

def get_smart_transcript(video_id):
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
    print("מעביר ל-Gemini נתונים לעיבוד...", flush=True)
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
        print(f"שגיאה ב-AI: {e}", flush=True)
        return None

def post_to_site(title, content):
    api_url = f"{os.environ['SITE_URL']}/wp-json/wp/v2/posts"
    auth = (os.environ['SITE_USERNAME'], os.environ['SITE_PASSWORD'])
    data = {"title": title, "content": content, "status": "publish"}
    try:
        res = requests.post(api_url, json=data, auth=auth)
        return res.status_code
    except Exception as e:
        print(f"שגיאת תקשורת עם האתר: {e}", flush=True)
        return 500

if __name__ == "__main__":
    print("--- מתחיל ריצה אוטומטית (עם מנגנון גיבוי תיאור) ---", flush=True)
    
    processed = get_processed_videos()
    print(f"יש {len(processed)} סרטונים בזיכרון שטופלו בעבר.", flush=True)
    
    for channel_id in CHANNELS:
        print(f"ניגש למשוך RSS לערוץ: {channel_id}", flush=True)
        feed = get_channel_feed(channel_id)
        
        if not feed:
            print("הפיד חזר ריק או שגיאת חיבור (יוטיוב חסם זמנית את ה-RSS).", flush=True)
            continue
            
        if not feed.entries:
            print("הפיד תקין אך לא נמצאו בו סרטונים כלל.", flush=True)
            continue
            
        print(f"נמצאו {len(feed.entries)} סרטונים בפיד. מתחיל סריקה...", flush=True)
        
        video_processed_in_this_run = False
        
        for entry in feed.entries:
            v_id = entry.yt_videoid
            
            if v_id in processed:
                print(f"מדלג על הסרטון '{entry.title}' - כבר טופל בעבר.", flush=True)
                continue
                
            print(f"\n>> מתחיל עבודה על סרטון חדש: {entry.title}", flush=True)
            description = entry.summary if 'summary' in entry else "אין תיאור"
            
            text = get_smart_transcript(v_id)
            if text:
                print("התמלול נמשך בהצלחה! מכין כתבת עומק.", flush=True)
            else:
                print("התמלול נחסם. משתמש בתיאור הסרטון למבזק קצר.", flush=True)
            
            article = process_with_gemini(entry.title, description, text, entry.link)
            
            if article:
                status = post_to_site(entry.title, article)
                if status in [200, 201]:
                    print(f"הפוסט עלה לאתר! (קוד: {status})", flush=True)
                    mark_as_processed(v_id)
                    video_processed_in_this_run = True
                    break # יוצא מהלופ כדי לא לפרסם יותר מפוסט אחד בכל ריצה
                else:
                    print(f"שגיאה בפרסום לאתר: {status}", flush=True)
            else:
                print("שגיאה ביצירת התוכן מ-Gemini.", flush=True)
                
        if not video_processed_in_this_run:
            print("סיום: לא היו סרטונים חדשים לטפל בהם.", flush=True)
