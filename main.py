import os
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai

# הגדרת ה-Client של Gemini 2.0 Flash
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# נתוני סרטון ספציפי לבדיקה (COMEX Silver Delivery Shock)
TEST_VIDEO_ID = "6vOKEkg7Uyg"
TEST_VIDEO_TITLE = "COMEX Silver Delivery Shock: What Happens in March?"
TEST_VIDEO_URL = f"https://www.youtube.com/watch?v={TEST_VIDEO_ID}"

def get_transcript(video_id):
    """משיכת תמלול ישירה"""
    print(f"מנסה למשוך תמלול לסרטון: {video_id}...")
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['he', 'en'])
        text = " ".join([t['text'] for t in transcript_list])
        print("התמלול נמשך בהצלחה!")
        return text
    except Exception as e:
        print(f"שגיאה במשיכת תמלול: {e}")
        return None

def process_with_gemini(title, text, url):
    """כתיבת הכתבה בעברית"""
    print("מעביר ל-Gemini לכתיבת הכתבה...")
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
    """פרסום לאתר וורדפרס"""
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
    print("--- מתחיל בדיקת מעבדה: הזרקת סרטון ישירה ---")
    
    # שלב 1: תמלול
    text = get_transcript(TEST_VIDEO_ID)
    
    if text:
        # שלב 2: כתיבת כתבה
        article = process_with_gemini(TEST_VIDEO_TITLE, text, TEST_VIDEO_URL)
        
        if article:
            # שלב 3: פרסום
            status = post_to_site(TEST_VIDEO_TITLE, article)
            if status in [200, 201]:
                print(f"הצלחה מסחררת! הכתבה פורסמה. סטטוס: {status}")
            else:
                print(f"הכתבה נכתבה אבל האתר החזיר שגיאה: {status}")
        else:
            print("הבדיקה נכשלה בשלב ה-AI.")
    else:
        print("הבדיקה נכשלה בשלב התמלול. וודא שספריית התמלול מותקנת היטב.")
