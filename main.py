import os
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi # ייבוא ישיר ומתוקן
from google import genai

# הגדרת ה-Client החדש של Gemini (לפי המלצת הלוגים שלך)
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
    """
    מנסה למשוך תמלול. 
    אם הסרטון באנגלית, ה-AI יתרגם אותו לעברית בשלב הבא.
    """
    try:
        # כאן התיקון המרכזי - קריאה ישירה למחלקה
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        return " ".join([t['text'] for t in transcript_list])
    except Exception as e:
        print(f"שגיאה במשיכת תמלול: {e}")
        return None

def process_with_gemini(title, text, url):
    """מעבד כל תמלול (גם אנגלי) לכתבה איכותית בעברית"""
    prompt = f"""
    אתה עיתונאי כלכלי באתר 'Coinfolio'. 
    משימה: תרגם ועבד את התוכן הבא לכתבה עיתונאית מעניינת בעברית.
    כותרת הסרטון: {title}
    מקור (להוספה בסוף): {url}
    
    התמלול (עשוי להיות באנגלית):
    {text}
    """
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
    api_url = f"{os.environ['SITE_URL']}/wp-json/wp/v2/posts"
    auth = (os.environ['SITE_USERNAME'], os.environ['SITE_PASSWORD'])
    data = {"title": title, "content": content, "status": "publish"}
    res = requests.post(api_url, json=data, auth=auth)
    return res.status_code

if __name__ == "__main__":
    for channel_id in CHANNELS:
        feed = get_channel_feed(channel_id)
        if feed and feed.entries:
            entry = feed.entries[0] # סרטון בדיקה בודד
            print(f"נמצא סרטון: {entry.title}. מעבד...")
            
            transcript = get_transcript(entry.yt_videoid)
            if transcript:
                article = process_with_gemini(entry.title, transcript, entry.link)
                if article:
                    status = post_to_site(entry.title, article)
                    print(f"סטטוס פרסום באתר: {status}")
            else:
                print("לא נמצא תמלול לסרטון. וודא שיש כתוביות (CC) ביוטיוב.")
