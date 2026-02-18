import os
import google.generativeai as genai
import requests

# טעינת הגדרות
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.0-flash')

def test_setup():
    print("--- בודק חיבור ל-Gemini ---")
    response = model.generate_content("תגיד 'מערכת מוכנה לעבודה' בעברית")
    print(f"Gemini אומר: {response.text}")

    print("\n--- בודק חיבור לאתר ---")
    site_url = os.environ["SITE_URL"]
    # בדיקה שהאתר מגיב
    res = requests.get(f"{site_url}/wp-json/")
    if res.status_code == 200:
        print(f"האתר {site_url} מגיב מצוין!")
    else:
        print(f"שגיאה בחיבור לאתר: {res.status_code}")

if __name__ == "__main__":
    test_setup()
