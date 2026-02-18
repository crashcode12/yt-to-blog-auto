import os
import requests
import feedparser
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

# הגדרות Gemini 2.0 Flash
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash')

# הגדרת הערוץ: GoldCore TV
CHANNELS = ["UCFddgboLcMQ4IUE681qvcqg"] 

def get_channel_feed(channel_id):
    """מושך את פיד ה-RSS תוך שימוש ב-User-Agent כדי למנוע חסימה"""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return feedparser.parse(response.content)
        else:
            print(f"שגיאה במשיכת הפיד מהערוץ {channel_id}: סטטוס {response.status_code}")
            return None
    except Exception as e:
        print(f"שגיאה בחיבור ליוטיוב: {e}")
        return None

def get_transcript(video_id):
    """מושך תמלול מהסרטון"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        print(f"לא ניתן היה למשוך תמלול לסרטון {video_id}: {e}")
        return None

def process_with_gemini(title, text, url):
    """מעבד את התמלול לכתבה בעברית עבור Coinfolio"""
    prompt = f"""
    אתה עיתונאי כלכלי מומחה באתר "Coinfolio". 
    הנה תמלול של סרטון יוטיוב חדש בנושא זהב והשקעות בשם: "{title}".
    
    משימה:
    1. כתוב כתבה מקצועית, מעניינת ומניעה לפעולה בעברית המבוססת על התוכן.
    2. השתמש בכותרות משנה (H2, H3) ובשפה רהוטה.
    3. בסוף הכתבה, הוסף פסקה קצרה של "דעה אישית" מבוססת תוכן הסרטון.
    4. הוסף קרדיט ברור: "מקור: {url}".
    
    התמלול: {text}
    """
    response = model.generate_content(prompt)
    return response.text

def post_to_site(title, content):
    """מפרסם את הכתבה לאתר וורדפרס"""
    api_url = f"{os.environ['SITE_URL']}/wp-json/wp/v2/posts"
    auth = (os.environ['SITE_USERNAME'], os.environ['SITE_PASSWORD'])
    data = {
        "title": title,
        "content": content,
        "status": "publish" 
    }
    res = requests.post(api_url, json=data, auth=auth)
    return res.status_code

if __name__ == "__main__":
    for channel_id in CHANNELS:
        print(f"בודק סרטונים עבור ערוץ: {channel_id}")
        feed = get_channel_feed(channel_id)
        
        if feed and feed.entries:
            # הזרקה של סרטון אחד בלבד (האחרון בפיד) לצורך בדיקה
            entry = feed.entries[0] 
            print(f"נמצא סרטון: {entry.title}. מתחיל עיבוד...")
            
            transcript_text = get_transcript(entry.yt_videoid)
            
            if transcript_text:
                final_article = process_with_gemini(entry.title, transcript_text, entry.link)
                status = post_to_site(entry.title, final_article)
                print(f"סטטוס פרסום באתר: {status}")
            else:
                print("הבדיקה נכשלה: לא נמצא תמלול לסרטון.")
        else:
            print("לא נמצאו סרטונים בפיד ה-RSS או שהגישה נחסמה.")
