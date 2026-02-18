import os
import requests
import feedparser
import youtube_transcript_api
from google import genai

# הגדרת ה-Client החדש של Gemini (לפי המלצת הלוגים שלך)
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# הגדרת הערוץ: GoldCore TV
CHANNELS = ["UCFddgboLcMQ4IUE681qvcqg"] 

def get_channel_feed(channel_id):
    """מושך את ה-RSS עם User-Agent למניעת חסימות"""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return feedparser.parse(response.content)
        return None
    except Exception as e:
        print(f"שגיאה בגישה ליוטיוב: {e}")
        return None

def get_transcript(video_id):
    """מתקן את השגיאה שראינו בלוגים - קריאה ישירה דרך המודול"""
    try:
        # שימוש בגישה הישירה למניעת ה-AttributeError
        transcript_list = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        return " ".join([t['text'] for t in transcript_list])
    except Exception as e:
        print(f"לא ניתן היה למשוך תמלול לסרטון {video_id}: {e}")
        return None

def process_with_gemini(title, text, url):
    """שימוש במודל Gemini 2.0 Flash בפורמט ה-API החדש"""
    prompt = f"אתה עיתונאי כלכלי ב-'Coinfolio'. כתוב כתבה מקצועית בעברית על: {title}. תמלול: {text}. מקור: {url}"
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"שגיאה בעיבוד ה-AI: {e}")
        return None

def post_to_site(title, content):
    """פרסום לוורדפרס"""
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
            
            transcript = get_transcript(entry.yt_videoid)
            if transcript:
                article = process_with_gemini(entry.title, transcript, entry.link)
                if article:
                    status = post_to_site(entry.title, article)
                    print(f"הסרטון פורסם בהצלחה! סטטוס באתר: {status}")
            else:
                print("הבדיקה נכשלה: לא נמצא תמלול.")
