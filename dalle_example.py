
# DALL-E 3 사용 예제 (OpenAI API Key 필요)
from openai import OpenAI

client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

response = client.images.generate(
    model="dall-e-3",
    prompt="썬그라스를 낀 케이팝 여성 싱어를 남대문 배경으로",
    size="1024x1024",
    quality="standard",
    n=1,
)

image_url = response.data[0].url
print(f"Generated image URL: {image_url}")

# 이미지 다운로드
import requests
img_response = requests.get(image_url)
with open("kpop_singer.png", "wb") as f:
    f.write(img_response.content)
print("이미지 저장 완료!")
