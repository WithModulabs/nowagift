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
API_URL = "https://api-singapore.klingai.com/v1/videos/image2video"  # 실제 엔드포인트로 교체

# 요청 헤더
headers = {
    "Authorization": f"Bearer {api_token}",
    "Content-Type": "application/json"
}

# 요청 바디 (예시)
test_data = {
    "model_name": "kling-v1",
    "mode": "pro",
    "duration": "5",
    "image": "https://h2.inkwai.com/bs2/upload-ylab-stunt/se/ai_portal_queue_mmu_image_upscale_aiweb/3214b798-e1b4-4b00-b7af-72b5b0417420_raw_image_0.jpg",
    "prompt": "The astronaut stood up and walked away",
    "cfg_scale": 0.5,
    "static_mask": "https://h2.inkwai.com/bs2/upload-ylab-stunt/ai_portal/1732888177/cOLNrShrSO/static_mask.png",
    "dynamic_masks": [
      {
        "mask": "https://h2.inkwai.com/bs2/upload-ylab-stunt/ai_portal/1732888130/WU8spl23dA/dynamic_mask_1.png",
        "trajectories": [
          {"x":279,"y":219},{"x":417,"y":65}
        ]
      }
    ]
}

data = {
    "model_name": "kling-v2-1",
    "mode": "pro",
    "duration": "10",
    "image": "https://raw.githubusercontent.com/robertchoi/now-a-gift/refs/heads/main/images/1.png",
    "prompt": "happy and peaceful moments",
    "cfg_scale": 0.5,
}



# API 호출
response = requests.post(API_URL, headers=headers, json=data)

# 결과 처리
if response.status_code == 200:
    result = response.json()
    if "data" in result:
        data = result["data"]
        task_id = data.get("task_id")
        task_status = data.get("task_status")
        print(f"Task ID: {task_id}")
        print(f"Task Status: {task_status}")
        # 필요시 추가 정보 출력
        if "task_info" in data:
            print(f"Task Info: {data['task_info']}")
        print(f"Created At: {data.get('created_at')}")
        print(f"Updated At: {data.get('updated_at')}")

        # --- Polling for task completion ---
        import sys
        POLL_URL = f"https://api-singapore.klingai.com/v1/videos/image2video/{task_id}"
        max_wait = 30 * 2 * 10  # seconds
        interval = 1   # seconds
        for i in range(max_wait):
            poll_response = requests.get(POLL_URL, headers=headers)
            if poll_response.status_code == 200:
                poll_result = poll_response.json()
                poll_data = poll_result.get("data", {})
                poll_status = poll_data.get("task_status")
                print(f"[Polling] {i+1}s: Task Status: {poll_status}")
                if poll_status == "succeed":
                    videos = poll_data.get("task_result", {}).get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        print(f"\n생성된 비디오 URL: {video_url}")
                        # 비디오 다운로드
                        try:
                            video_response = requests.get(video_url, stream=True)
                            if video_response.status_code == 200:
                                filename = f"{task_id}.mp4"
                                with open(filename, "wb") as f:
                                    for chunk in video_response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                print(f"비디오가 성공적으로 다운로드되었습니다: {filename}")
                            else:
                                print(f"비디오 다운로드 실패: {video_response.status_code}, {video_response.text}")
                        except Exception as e:
                            print(f"비디오 다운로드 중 오류 발생: {e}")
                    else:
                        print("\n'succeed' 상태이나 비디오 정보가 없습니다.")
                    break
                elif poll_status == "failed":
                    fail_msg = poll_data.get("task_status_msg", "실패 사유 없음")
                    print(f"\nTask failed: {fail_msg}")
                    break
            else:
                print(f"[Polling] {i+1}s: API call failed: {poll_response.status_code}, {poll_response.text}")
            time.sleep(interval)
        else:
            print("\n30초 내에 작업이 완료되지 않았습니다.")
    else:
        print("응답에 'data' 필드가 없습니다. 전체 응답:", result)
else:
    try:
        error_result = response.json()
        print(f"API call failed: {response.status_code}, message: {error_result.get('message')}, code: {error_result.get('code')}, request_id: {error_result.get('request_id')}")
    except Exception:
        print("API call failed:", response.status_code, response.text)