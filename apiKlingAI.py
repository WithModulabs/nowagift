import os
import time
try:
    import jwt
    # Test if jwt.encode exists
    if not hasattr(jwt, 'encode'):
        raise ImportError("JWT module missing encode method")
except ImportError:
    # Fallback: try explicit PyJWT import
    import PyJWT as jwt
import requests
from dotenv import load_dotenv

# KlingAI API: video generation

class KlingAIAPI:
    def __init__(self, ak: str, sk: str):
        self.ak = ak
        self.sk = sk
        self.base_url = "https://api-singapore.klingai.com/v1"

    # jwt 토큰 생성 및 반환
    def _get_api_token(self):
        payload = {
            "iss": self.ak,
            "exp": int(time.time()) + 1800,  # 30분 유효
            "nbf": int(time.time()) - 5
        }
        token = jwt.encode(payload, self.sk, algorithm="HS256")
        return token

    def _get_headers(self):
        api_token = self._get_api_token()
        return {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def generate_video(self, data: dict):
        url = f"{self.base_url}/videos/image2video"
        headers = self._get_headers()
        
        print("비디오 생성 작업을 시작합니다.")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # HTTP 오류 시 예외 발생
        
        return response.json()

    # 특정 작업의 ID 상태 조회 (task_id: 상태를 확인할 작업 ID)
    def check_task_status(self, task_id: str):
        url = f"{self.base_url}/videos/image2video/{task_id}"
        headers = self._get_headers()
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()

if __name__ == "__main__":
    load_dotenv()
    AK = os.environ.get("AK")
    SK = os.environ.get("SK")

    # KlingAI API 객체 생성
    klingai = KlingAIAPI(ak=AK, sk=SK)

    # 비디오 생성에 사용할 데이터
    video_data = {
        "model_name": "kling-v2-1",
        "mode": "pro",
        "duration": "10",
        "image": "https://raw.githubusercontent.com/robertchoi/now-a-gift/refs/heads/main/resources/image/1.png",
        "prompt": "happy and peaceful moments",
        "cfg_scale": 0.5,
    }

    try:
        # 1. 비디오 생성 요청
        init_response = klingai.generate_video(video_data)
        task_data = init_response.get("data", {})
        task_id = task_data.get("task_id")
        
        if not task_id:
            raise ValueError("API 응답에서 task_id를 찾을 수 없습니다.")
            
        print(f"Task ID: {task_id}")
        
        # 2. 작업 상태 폴링
        max_wait = 300  # 최대 대기 시간 (5분)
        interval = 5    # 폴링 간격 (5초)
        start_time = time.time()
        
        print("\n비디오 생성이 완료될 때까지 대기합니다...")
        
        while time.time() - start_time < max_wait:
            status_response = klingai.check_task_status(task_id)
            poll_data = status_response.get("data", {})
            poll_status = poll_data.get("task_status")
            
            print(f"[{int(time.time() - start_time)}s 경과] 현재 상태: {poll_status}")
            
            if poll_status == "succeed":
                videos = poll_data.get("task_result", {}).get("videos", [])
                if videos:
                    video_url = videos[0].get("url")
                    print(f"\n비디오 생성 성공!")
                    print(f"URL: {video_url}")
                    
                    # 3. 비디오 다운로드
                    print(f"비디오를 다운로드합니다: {task_id}.mp4")
                    video_response = requests.get(video_url, stream=True)
                    video_response.raise_for_status()
                    
                    filename = f"{task_id}.mp4"
                    with open(filename, "wb") as f:
                        for chunk in video_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"다운로드 완료: {filename}")
                else:
                    print("비디오 정보가 응답에 포함되어 있지 않습니다.")
                break
            
            elif poll_status == "failed":
                fail_msg = poll_data.get("task_status_msg", "실패 사유 알 수 없음")
                print(f"비디오 생성 실패: {fail_msg}")
                break
                
            time.sleep(interval)
        else:
            print(f"\n최대 대기 시간({max_wait}s) 초과. 작업이 완료되지 않았습니다.")
            
    except requests.exceptions.RequestException as e:
        print(f"API 호출 중 오류 발생: {e}")
    except ValueError as e:
        print(f"데이터 오류: {e}")
    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")