import os
import requests
import feedparser
import youtube_transcript_api
from google import genai

# הגדרת ה-Client של Gemini 2.0 Flash
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# ערוץ GoldCore TV
CHANNELS = ["UCFddgboLcMQ4IUE681qvcqg"] 

def get_channel_feed(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return feedparser.parse(response.content) if response.status_code == 200 else None
    except:
        return None

def get_transcript(video_id):
    """שיטה עוקפת-שגיאות למשיכת תמלול"""
    try:
        # כאן התיקון הקריטי למניעת ה-AttributeError:
        # אנחנו ניגשים ישירות למחלקה דרך המודול שייבאנו
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        return " ".join([t['text'] for t in transcript_list])
    except Exception as e:
        print(f"שגיאה במשיכת תמלול לסרטון {video_id}: {e}")
        return None

def process_with_gemini(title, text, url):
    """הפיכת התמלול לכתבה מקצועית בעברית"""
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
    """פרסום לוורדפרס"""
    api_url = f"{os.environ['SITE_URL']}/wp-json/wp/v2/posts"
    auth = (os.environ['SITE_USERNAME'], os.environ['SITE_PASSWORD'])
    data = {"title": title, "content": content, "status": "publish"}
    try:
        res = requests.post(api_url, json=data, auth=auth)
        return res.status_code
    except:
        return 500

if __name__ == "__main__":
    for channel_id in CHANNELS:
        feed = get_channel_feed(channel_id)
        if feed and feed.entries:
            entry = feed.entries[0] # מעבד רק את הסרטון הכי חדש לבדיקה
            print(f"נמצא סרטון: {entry.title}. מעבד...")
            
            text = get_transcript(entry.yt_videoid)
            if text:
                article = process_with_gemini(entry.title, text, entry.link)
                if article:
                    status = post_to_site(entry.title, article)
                    print(f"הסרטון פורסם בהצלחה! סטטוס באתר: {status}")
            else:
                print("הבדיקה נכשלה: לא נמצא תמלול. וודא שהסרטון ביוטיוב תומך ב-CC.")
