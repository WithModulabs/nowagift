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

def encode_image_to_base64(image_path):
    """이미지 파일을 base64로 인코딩"""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ 이미지 파일을 찾을 수 없습니다: {image_path}")
        return None
    except Exception as e:
        print(f"❌ 이미지 인코딩 중 오류 발생: {e}")
        return None

# 첨부할 이미지 파일 경로
image_path = "D:/git/nowagift/kpop_singer_20250908_202502_1.png"

# 이미지를 base64로 인코딩
base64_image = encode_image_to_base64(image_path)

if not base64_image:
    print("이미지 처리에 실패했습니다.")
    exit(1)

print("이미지 파일을 성공적으로 인코딩했습니다.")

# API 요청 설정
url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {APIK}",
    "Content-Type": "application/json",
    "HTTP-Referer": YOUR_SITE_URL or "",
    "X-Title": YOUR_SITE_NAME or "",
}

# 이미지와 함께 전송할 프롬프트
prompt = "이 이미지의 배경을 제주도 한라산과 바다로 바꿔주세요. 인물은 그대로 유지하고 배경만 제주도의 아름다운 자연경관으로 변경해주세요."

payload = {
    "model": "google/gemini-2.5-flash-image-preview",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    "modalities": ["image", "text"]
}

print("API 요청을 전송 중...")
response = requests.post(url, headers=headers, json=payload)

print("Status Code:", response.status_code)
result = response.json()
print("Response:", json.dumps(result, indent=2, ensure_ascii=False))

# 생성된 이미지 처리
if result.get("choices"):
    message = result["choices"][0]["message"]
    print("Message content:", message.get("content"))
    
    if message.get("images"):
        for i, image in enumerate(message["images"]):
            image_url = image["image_url"]["url"]
            
            # Extract base64 data from data URL
            if image_url.startswith("data:image/"):
                header, data = image_url.split(",", 1)
                image_data = base64.b64decode(data)
                
                # Save image with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"jeju_background_{timestamp}_{i+1}.png"
                
                with open(filename, "wb") as f:
                    f.write(image_data)
                
                print(f"제주도 배경으로 변경된 이미지가 '{filename}'로 저장되었습니다!")
            else:
                print("Unexpected image URL format:", image_url)
    else:
        print("❌ 응답에서 이미지를 찾을 수 없습니다.")
        print("텍스트 응답:", message.get("content", "응답 없음"))
else:
    print("❌ API 요청이 실패했습니다.")
    if result.get("error"):
        print("오류:", result["error"])