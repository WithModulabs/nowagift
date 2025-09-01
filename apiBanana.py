import openai
import os
import time
import requests
import re
import base64
from dotenv import load_dotenv

# Poe API를 통한 Banana 이미지 생성 및 다운로드

class BananaAPI:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.poe.com/v1",
        )

    def encode_image_to_base64(self, image_path: str):
        """이미지를 base64로 인코딩"""
        try:
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded
        except Exception as e:
            print(f"이미지 인코딩 오류: {e}")
            return None

    def generate_image(self, prompt: str, image_path: str = None):
        """이미지 생성 요청 (첨부 이미지 포함)"""
        print(f"이미지 생성 요청: {prompt}")
        if image_path:
            print(f"첨부 이미지: {image_path}")
        
        messages = [{"role": "user", "content": prompt}]
        
        # 이미지가 첨부된 경우 base64로 인코딩하여 메시지에 추가
        if image_path and os.path.exists(image_path):
            encoded_image = self.encode_image_to_base64(image_path)
            if encoded_image:
                # OpenAI 형식에 따라 이미지를 메시지에 포함
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                        }
                    ]
                }]
        
        chat = self.client.chat.completions.create(
            model="Gemini-2.5-Flash-Image",
            messages=messages,
        )
        
        response_content = chat.choices[0].message.content
        print(f"응답: {response_content}")
        
        return response_content

    def extract_image_url(self, response_content: str):
        """응답에서 이미지 URL 추출"""
        # 이미지 URL 패턴 매칭 (http/https로 시작하는 URL)
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.(jpg|jpeg|png|gif|bmp|webp)'
        urls = re.findall(url_pattern, response_content, re.IGNORECASE)
        
        if urls:
            return urls[0][0] + '.' + urls[0][1]  # URL + 확장자
        
        # 더 일반적인 URL 패턴
        general_url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        general_urls = re.findall(general_url_pattern, response_content)
        
        for url in general_urls:
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']):
                return url
                
        return None

    def download_image(self, image_url: str, output_dir: str = ".", filename: str = None):
        """이미지 파일 다운로드"""
        try:
            if not filename:
                # URL에서 파일명 추출 또는 기본 파일명 생성
                if '/' in image_url:
                    filename = image_url.split('/')[-1]
                    if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                        filename = f"banana_image_{int(time.time())}.png"
                else:
                    filename = f"banana_image_{int(time.time())}.png"
            
            file_path = os.path.join(output_dir, filename)
            
            print(f"이미지를 다운로드합니다: {image_url}")
            print(f"저장 경로: {file_path}")
            
            # 출력 디렉토리가 없으면 생성
            os.makedirs(output_dir, exist_ok=True)
            
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"다운로드 완료: {file_path}")
            return {
                "success": True,
                "file_path": file_path,
                "message": "다운로드 성공"
            }
            
        except Exception as e:
            return {
                "success": False,
                "file_path": None,
                "message": f"다운로드 실패: {e}"
            }

    def generate_and_download(self, prompt: str, output_dir: str = ".", filename: str = None, max_retries: int = 3, image_path: str = None):
        """
        이미지 생성 요청부터 다운로드까지 전체 프로세스 실행
        
        Args:
            prompt: 이미지 생성 프롬프트
            output_dir: 다운로드할 디렉토리 경로
            filename: 저장할 파일명 (None이면 자동 생성)
            max_retries: 재시도 횟수
            image_path: 첨부할 이미지 파일 경로 (None이면 텍스트만)
        
        Returns:
            dict: {"success": bool, "file_path": str, "message": str, "response": str}
        """
        for attempt in range(max_retries):
            try:
                print(f"시도 {attempt + 1}/{max_retries}")
                
                # 이미지 생성 요청
                response_content = self.generate_image(prompt, image_path)
                
                # URL 추출
                image_url = self.extract_image_url(response_content)
                
                if not image_url:
                    print("응답에서 이미지 URL을 찾을 수 없습니다.")
                    if attempt < max_retries - 1:
                        print("재시도합니다...")
                        time.sleep(5)
                        continue
                    else:
                        return {
                            "success": False,
                            "file_path": None,
                            "message": "이미지 URL을 찾을 수 없습니다.",
                            "response": response_content
                        }
                
                print(f"이미지 URL 발견: {image_url}")
                
                # 이미지 다운로드
                download_result = self.download_image(image_url, output_dir, filename)
                download_result["response"] = response_content
                
                return download_result
                
            except Exception as e:
                print(f"오류 발생: {e}")
                if attempt < max_retries - 1:
                    print("재시도합니다...")
                    time.sleep(5)
                else:
                    return {
                        "success": False,
                        "file_path": None,
                        "message": f"처리 중 오류 발생: {e}",
                        "response": None
                    }

if __name__ == "__main__":
    load_dotenv()
    POE_API_KEY = os.environ.get("POE_API_KEY")
    
    if not POE_API_KEY:
        # 하드코딩된 키 사용 (보안상 권장하지 않음)
        POE_API_KEY = "F39BTBYCg0tAq57cHRV3qXLl2tmFPH1VDS2hC0mnvo4"
    
    # Banana API 객체 생성
    banana = BananaAPI(api_key=POE_API_KEY)
    
    try:
        # 이미지 생성 및 다운로드
        prompt = "저녁에 썬그라쓰를 쓴 K-POP 소녀"
        sample_image_path = "resources/image/1.png"  # 첨부할 이미지 경로 (선택사항)
        
        print("이미지 생성 및 다운로드를 시작합니다...")
        result = banana.generate_and_download(
            prompt=prompt,
            output_dir="temp",
            filename=None,
            image_path=sample_image_path if os.path.exists(sample_image_path) else None
        )
        
        if result["success"]:
            print(f"성공: {result['message']}")
            print(f"파일 경로: {result['file_path']}")
        else:
            print(f"실패: {result['message']}")
            if result.get("response"):
                print(f"서버 응답:\n{result['response']}")
                
    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")