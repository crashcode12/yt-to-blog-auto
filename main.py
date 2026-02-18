import os
import feedparser
import requests
from google import genai

# הגדרת ה-Client של Gemini 2.0
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# שתי דרכים שונות לגשת לפיד של GoldCore TV למקרה שיוטיוב מחזירה 404
RSS_URLS = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCFddgboLcMQ4IUE681qvcqg",
    "https://www.youtube.com/feeds/videos.xml?user=GoldCoreLimited"
]

DB_FILE = "processed_videos.txt"

def get_processed_videos():
    if not os.path.exists(DB_FILE):
        return set()
    with open(DB_FILE, "r") as f:
        return set(f.read().splitlines())

def mark_as_processed(video_id):
    with open(DB_FILE, "a") as f:
        f.write(f"{video_id}\n")

def process_with_gemini(title, description, url):
    print("מעביר ל-Gemini את התקציר לעריכה...", flush=True)
    
    prompt = f"""
    אתה עיתונאי כלכלי באתר 'Coinfolio'.
    לפניך כותרת ותקציר (תיאור) של סרטון יוטיוב חדש.
    
    כותרת הסרטון: {title}
    תקציר הסרטון: {description}
    
    משימה:
    כתוב "מבזק חדשות" קצר, מרתק ומקצועי בעברית (פסקה אחת או שתיים) המבוסס *אך ורק* על הכותרת והתקציר.
    נקה טקסטים שיווקיים של יוטיוב (כמו "לחצו כאן להרשמה" או לינקים לרשתות חברתיות).
    בסוף המבזק, הוסף את השורה: "לצפייה בסרטון המלא: {url}".
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
    print("--- מתחיל ריצה: אסטרטגיית תקציר בלבד (ללא תמלול) ---", flush=True)
    
    processed = get_processed_videos()
    print(f"יש {len(processed)} סרטונים בזיכרון שטופלו בעבר.", flush=True)
    
    feed = None
    # מנסים את הכתובות אחת אחרי השנייה כדי למנוע את שגיאת ה-404
    for rss_url in RSS_URLS:
        print(f"מנסה למשוך RSS מכתובת גישה: {rss_url}", flush=True)
        temp_feed = feedparser.parse(rss_url) # שימוש ישיר שעוקף חסימות User-Agent
        if temp_feed and temp_feed.entries:
            feed = temp_feed
            print("הפיד נמשך בהצלחה!", flush=True)
            break
            
    if not feed or not feed.entries:
        print("לא הצלחנו למשוך סרטונים משום כתובת. יוטיוב חוסמת זמנית את הפיד.", flush=True)
        exit()
        
    for entry in feed.entries:
        v_id = entry.yt_videoid
        
        if v_id in processed:
            print(f"מדלג על '{entry.title}' - כבר פורסם.", flush=True)
            continue
            
        print(f"\n>> מתחיל עבודה על סרטון חדש: {entry.title}", flush=True)
        
        # שלב המפתח: שולפים את התיאור בלבד!
        description = entry.summary if 'summary' in entry else "אין תיאור"
        print("התקציר נמשך בהצלחה! מדלג על שלב התמלול ומעביר לניסוח.", flush=True)
        
        article = process_with_gemini(entry.title, description, entry.link)
        
        if article:
            status = post_to_site(entry.title, article)
            if status in [200, 201]:
                print(f"הפוסט עלה לאתר! (קוד: {status})", flush=True)
                mark_as_processed(v_id)
                break # ברגע שפורסם אחד בהצלחה, עוצרים.
            else:
                print(f"שגיאה בפרסום לוורדפרס: {status}", flush=True)
        else:
            print("שגיאה ביצירת התוכן.", flush=True)
