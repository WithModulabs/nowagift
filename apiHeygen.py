import requests
import os
from dotenv import load_dotenv

class HeygenAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.heygen.com/v2/photo_avatar"

    def generate_avatar_photo(self, image_path: str, name: str, age: str, gender: str, ethnicity: str, orientation: str, pose: str, style: str, appearance: str):
        import base64
        url = f"{self.base_url}/photo/generate"
        with open(image_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode("utf-8")
        payload = {
            "name": name,
            "age": age,
            "gender": gender,
            "ethnicity": ethnicity,
            "orientation": orientation,
            "pose": pose,
            "style": style,
            "appearance": appearance,
            "photo": img_base64
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json()

    def check_generation_status(self, generation_id: str):
        url = f"{self.base_url}/generation/{generation_id}"
        headers = {
            "accept": "application/json",
            "X-Api-Key": self.api_key
        }
        response = requests.get(url, headers=headers)
        return response.json()

if __name__ == "__main__":
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    api_key = os.getenv("HEYGEN_API_KEY")  # .env 파일에 HEYGEN_API_KEY=... 추가
    print("API Key:", api_key)
    image_path = "images/2.png"  # 첨부할 사진 경로
    heygen = HeygenAPI(api_key)
    result = heygen.generate_avatar_photo(
        image_path=image_path,
        name="Tom",
        age="Late Middle Age",
        gender="Man",
        ethnicity="East Asian",
        orientation="horizontal",
        pose="half_body",
        style="Vintage",   # 또는 "Realistic"
        appearance="A headshot of a casually dressed person. A mild smile and a relaxed expression. The background is made cleanly white. retro style [Landscape, Upper Body, Vintage/Realistic]"
    )
    print(result)
    # 생성 ID로 상태 확인 (폴링)
    import time
    if result.get("data") and result["data"].get("generation_id"):
        generation_id = result["data"]["generation_id"]
        while True:
            status = heygen.check_generation_status(generation_id)
            print(status)
            if status.get("data") and status["data"].get("status") == "success":
                print("완료!")
                # 이미지 다운로드
                image_urls = status["data"].get("image_url_list", [])
                for idx, img_url in enumerate(image_urls):
                    img_resp = requests.get(img_url)
                    if img_resp.status_code == 200:
                        filename = f"downloaded_avatar_{generation_id}_{idx+1}.jpg"
                        with open(filename, "wb") as f:
                            f.write(img_resp.content)
                        print(f"Downloaded: {filename}")
                    else:
                        print(f"Failed to download image {idx+1}: {img_url}")
                break
            time.sleep(5)  # 5초 대기 후 재시도
