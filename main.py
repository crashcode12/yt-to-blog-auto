import os
import time
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# הגדרות Gemini 2.0 Flash
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash')

# הגדרות אתר ויוטיוב
CHANNELS = ["UC_x5XG1OV2P6uZZ5FSM9Ttw"] # החלף ב-IDs של הערוצים שאתה רוצה
DB_FILE = "processed_videos.txt"

def get_processed_videos():
    if not os.path.exists(DB_FILE):
        return set()
    with open(DB_FILE, "r") as f:
        return set(f.read().splitlines())

def mark_as_processed(video_id):
    with open(DB_FILE, "a") as f:
        f.write(f"{video_id}\n")

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        print(f"לא נמצא תמלול לסרטון {video_id}: {e}")
        return None

def create_article(title, text, video_url):
    prompt = f"""
    אתה עיתונאי מקצועי באתר "Coinfolio". 
    הנה תמלול של סרטון יוטיוב: "{title}".
    משימה:
    1. אם התמלול ארוך (מעל 400 מילים), כתוב כתבה מעמיקה בעברית עם כותרות משנה.
    2. אם הוא קצר, כתוב "אנקדוטה" מעניינת (פסקה אחת).
    3. בסוף, הוסף: "קרדיט למקור: {video_url}".
    התמלול: {text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"שגיאה ב-Gemini: {e}")
        return None

def post_to_wordpress(title, content):
    api_url = f"{os.environ['SITE_URL']}/wp-json/wp/v2/posts"
    auth = (os.environ['SITE_USERNAME'], os.environ['SITE_PASSWORD'])
    data = {"title": title, "content": content, "status": "publish"}
    
    res = requests.post(api_url, json=data, auth=auth)
    return res.status_code

if __name__ == "__main__":
    processed = get_processed_videos()
    
    for channel_id in CHANNELS:
        feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
        
        for entry in feed.entries[:3]: # בודק את 3 הסרטונים האחרונים בכל ערוץ
            v_id = entry.yt_videoid
            if v_id in processed:
                continue
            
            print(f"מעבד סרטון חדש: {entry.title}")
            text = get_transcript(v_id)
            
            if text:
                article = create_article(entry.title, text, entry.link)
                if article:
                    status = post_to_wordpress(entry.title, article)
                    if status in [200, 201]:
                        print(f"פורסם בהצלחה! ({status})")
                        mark_as_processed(v_id)
                        time.sleep(10) # השהייה קלה למניעת חריגת Rate Limit
