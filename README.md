
# nowagift

## 프로젝트 개요
Kling AI NEW API를 활용한 이미지 생성 예제 및 JWT 기반 인증 토큰 생성 예제 코드입니다.

## 환경 준비

### 1. 파이썬 가상환경(venv) 생성 및 활성화
윈도우 기준 명령어:
```
python -m venv venv
.\venv\Scripts\activate
```

### 2. 필수 패키지 설치
```
pip install -r requirements.txt
```

### 3. .env 파일 생성
프로젝트 루트에 `.env` 파일을 생성하고 아래와 같이 입력하세요:
```
AK=your_access_key
SK=your_secret_key
```

## 예제 실행 방법

### 1. JWT 토큰 생성 및 이미지 생성 API 호출
`apiToken.py` 파일을 실행하면 JWT 토큰을 생성하고, Kling AI 이미지 생성 API를 호출합니다.

```
python apiToken.py
```

- API 엔드포인트, 파라미터 등은 Kling AI 공식 문서에 맞게 수정하세요.
- 네트워크 환경 또는 엔드포인트 오류 시 README의 안내를 참고해 문제를 해결하세요.

## 주요 파일 설명
- `apiToken.py` : JWT 토큰 생성 및 이미지 생성 API 호출 예제
- `requirements.txt` : 필요한 파이썬 패키지 목록
- `.env` : Access Key, Secret Key 등 민감 정보 환경변수 파일(직접 생성 필요)

## 의존성 설치 (uv 사용)


아래 명령어로 requirements.txt의 모든 의존성을 설치할 수 있습니다:

```powershell
uv add -r requirements.txt
```

설치된 패키지 목록을 requirements.txt로 저장하려면 아래 명령어를 사용하세요:

```powershell
uv pip freeze > requirements.txt
```

## Streamlit 앱 실행

### 로컬 실행
```bash
uv run streamlit run app.py
```

### 서버 실행 (외부 접속 허용)
```bash
uv run streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

**현재 서버 주소: http://15.165.13.49:8501**

## 백그라운드에서 Streamlit 앱 실행 (tmux 사용)

1. tmux 세션 시작
	```bash
	tmux new -s streamlit
	```
2. Streamlit 앱 실행
	 - 로컬에서 실행:
		 ```bash
		 uv run streamlit run your_app.py
		 ```
	 - 서버(외부 접속 허용)에서 실행:
		 ```bash
		 uv run streamlit run app.py --server.address 0.0.0.0 --server.port 8501
		 ```

3. tmux 세션에서 빠져나오기 (앱은 계속 실행됨)
	- Ctrl+b 누른 후 d

4. tmux에서 앱(세션) 중지 및 종료
	- tmux 세션에 다시 접속:
	  ```bash
	  tmux attach -t streamlit
	  ```
	- 실행 중인 streamlit 앱을 중지: Ctrl+C
	- tmux 세션 종료: exit 입력 또는 Ctrl+d






## 참고
- 공식 문서의 엔드포인트, 파라미터, 응답 구조에 따라 코드를 수정해야 할 수 있습니다.
- 네트워크 연결, 방화벽, VPN 등 환경에 따라 API 호출이 제한될 수 있습니다.

