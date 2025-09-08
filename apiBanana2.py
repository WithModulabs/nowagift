import requests
import json
import base64
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
APIK = os.getenv('OPENROUTER_API_KEY')
YOUR_SITE_URL = os.getenv('YOUR_SITE_URL')
YOUR_SITE_NAME = os.getenv('YOUR_SITE_NAME')

# Check if API key is loaded
if not APIK:
    print("❌ OPENROUTER_API_KEY가 .env 파일에 설정되지 않았습니다.")
    print("   .env 파일에 다음과 같이 추가해주세요:")
    print("   OPENROUTER_API_KEY=sk-or-v1-your-api-key-here")
    exit(1)

prompt = "썬그라스를 낀 케이팝 여성 싱어를 남대문 배경으로 그려줘 (Generate a K-pop female singer wearing sunglasses with Namdaemun gate in the background)"
url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {APIK}",
    "Content-Type": "application/json",
    "HTTP-Referer": YOUR_SITE_URL or "", # Optional. Site URL for rankings on openrouter.ai.
    "X-Title": YOUR_SITE_NAME or "", # Optional. Site title for rankings on openrouter.ai.
}
payload = {
    "model": "google/gemini-2.5-flash-image-preview",
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ],
    "modalities": ["image", "text"]
}

print("Generating image...")
response = requests.post(url, headers=headers, json=payload)
result = response.json()

print("Status Code:", response.status_code)
print("Response:", json.dumps(result, indent=2, ensure_ascii=False))

# The generated image will be in the assistant message
if result.get("choices"):
    message = result["choices"][0]["message"]
    print("Message content:", message.get("content"))
    
    if message.get("images"):
        for i, image in enumerate(message["images"]):
            image_url = image["image_url"]["url"]  # Base64 data URL
            
            # Extract base64 data from data URL
            if image_url.startswith("data:image/"):
                # Format: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
                header, data = image_url.split(",", 1)
                image_data = base64.b64decode(data)
                
                # Save image with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"kpop_singer_{timestamp}_{i+1}.png"
                
                with open(filename, "wb") as f:
                    f.write(image_data)
                
                print(f"이미지가 '{filename}'로 저장되었습니다!")
            else:
                print("Unexpected image URL format:", image_url)
    else:
        print("응답에서 이미지를 찾을 수 없습니다.")
else:
    print("API 요청이 실패했습니다.")