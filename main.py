import os
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi as YT_API # ייבוא עם שם ייחודי למניעת התנגשויות
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
    """שיטה חסינה יותר למשיכת תמלול שתפתור את ה-AttributeError"""
    try:
        # 1. קבלת רשימת כל הכתוביות הזמינות
        transcript_list = YT_API.list_transcripts(video_id)
        
        # 2. ניסיון למצוא עברית, ואם אין - אנגלית
        # זה עוקף את הבעיה שראינו בלוגים
        transcript = transcript_list.find_transcript(['he', 'en'])
        
        # 3. משיכת הטקסט בפועל
        data = transcript.fetch()
        return " ".join([t['text'] for t in data])
    except Exception as e:
        print(f"שגיאה במשיכת תמלול לסרטון {video_id}: {e}")
        return None

def process_with_gemini(title, text, url):
    """עיבוד התוכן לכתבה מקצועית בעברית"""
    prompt = f"""
    אתה עיתונאי כלכלי באתר 'Coinfolio'. 
    משימה: תרגם ועבד את התוכן הבא לכתבה עיתונאית מרתקת בעברית.
    כותרת הסרטון: {title}
    מקור (להוספה בסוף): {url}
    
    התמלול:
    {text}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"שגיאה ב-Gemini: {e}")
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
            entry = feed.entries[0] # בדיקה על סרטון בודד
            print(f"נמצא סרטון: {entry.title}. מעבד...")
            
            transcript_text = get_transcript(entry.yt_videoid)
            if transcript_text:
                article = process_with_gemini(entry.title, transcript_text, entry.link)
                if article:
                    status = post_to_site(entry.title, article)
                    print(f"הסרטון פורסם בהצלחה! סטטוס באתר: {status}")
            else:
                print("הבדיקה נכשלה: לא הצלחנו למשוך את הטקסט מהכתוביות.")
