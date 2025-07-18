import os
import time
import jwt
import requests
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
AK = os.environ.get("AK")
SK = os.environ.get("SK")

# JWT 토큰 생성 함수
def encode_jwt_token(ak, sk):
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    payload = {
        "iss": ak,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time()) - 5
    }
    token = jwt.encode(payload, sk, headers=headers)
    return token

# JWT 토큰 생성
api_token = encode_jwt_token(AK, SK)

# Kling AI NEW API 엔드포인트 (예시)
API_URL = "https://api-singapore.klingai.com/v1/images/generations"  # 실제 엔드포인트로 교체

# 요청 헤더
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

# 요청 바디 (예시)
data = {
    "prompt": "A futuristic cityscape at sunset, ultra-realistic, 8K",
    "n": 1
}

# API 호출
response = requests.post(API_URL, headers=headers, json=data)

# 결과 처리
if response.status_code == 200:
    result = response.json()
    # 예시: 이미지 URL이 result["images"][0]["url"]에 있다고 가정
    image_url = result["images"][0]["url"]
    print("생성된 이미지 URL:", image_url)
else:
    print("API 호출 실패:", response.status_code, response.text)