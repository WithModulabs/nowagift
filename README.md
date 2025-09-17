# nowagift

## 프로젝트 개요
Kling AI NEW API를 활용한 이미지 생성 예제 및 JWT 기반 인증 토큰 생성 예제 코드입니다.

## 환경 준비

### uv 설치

#### Windows
```powershell
# PowerShell (관리자 권한 권장)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 또는 pip 사용
pip install uv

# 또는 winget 사용
winget install --id=astral-sh.uv -e
```

#### Linux/macOS
```bash
# curl 사용 (권장)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 또는 pip 사용
pip install uv

# macOS의 경우 Homebrew 사용 가능
brew install uv
```

#### 설치 확인
```bash
uv --version
```


### 1. uv로 가상환경 생성 및 활성화
```bash
# 가상환경 생성
uv venv

# 가상환경 활성화 (Windows)
.venv\Scripts\activate

# 가상환경 활성화 (Linux/macOS)
source .venv/bin/activate
```

### 2. 프로젝트 의존성 동기화
```bash
# pyproject.toml의 의존성 설치
uv sync
```

### 3. 환경 변수 설정

#### 로컬 개발 환경
프로젝트 루트에 `.env` 파일을 생성하고 아래와 같이 입력하세요:
```
AK=your_access_key
SK=your_secret_key
HEYGEN_API_KEY=your_heygen_api_key
OPENAI_API_KEY=your_openai_api_key
```

#### AWS EC2 서버 환경
`.bashrc` 파일에 export 명령어로 환경 변수를 설정하세요:
```bash
# ~/.bashrc에 추가
export AK=your_access_key
export SK=your_secret_key
export HEYGEN_API_KEY=your_heygen_api_key
export OPENAI_API_KEY=your_openai_api_key

# 설정 적용
source ~/.bashrc
```

## 예제 실행 방법

### 1. JWT 토큰 생성 및 이미지 생성 API 호출
`apiToken.py` 파일을 실행하면 JWT 토큰을 생성하고, Kling AI 이미지 생성 API를 호출합니다.

```bash
# uv 가상환경에서 실행
uv run python apiToken.py
```

- API 엔드포인트, 파라미터 등은 Kling AI 공식 문서에 맞게 수정하세요.
- 네트워크 환경 또는 엔드포인트 오류 시 README의 안내를 참고해 문제를 해결하세요.

## 주요 파일 설명
- `apiToken.py` : JWT 토큰 생성 및 이미지 생성 API 호출 예제
- `pyproject.toml` : 프로젝트 의존성 및 설정 파일
- `uv.lock` : 정확한 의존성 버전 잠금 파일
- `.env` : Access Key, Secret Key 등 민감 정보 환경변수 파일(직접 생성 필요)

## 의존성 관리 (uv 사용)

### 새 패키지 추가
```bash
# 새 패키지 추가
uv add package_name

# 개발 전용 패키지 추가
uv add --dev package_name
```

### 의존성 동기화
```bash
# pyproject.toml과 uv.lock을 기반으로 의존성 동기화
uv sync

# 개발 의존성 제외하고 동기화
uv sync --no-dev
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
		 uv run streamlit run app.py
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


## 동영상 제작시에 서버 메모리 부족하여 스왑 파일 추가하여 해결

서버에서 Streamlit 등 앱이 자주 죽는다면 메모리 부족일 수 있습니다. 아래 명령어로 4GB 스왑 파일을 추가해보세요:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

재부팅 후에도 스왑이 유지되도록 아래 명령어로 /etc/fstab에 추가하세요:

```bash
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```





## 참고
- 공식 문서의 엔드포인트, 파라미터, 응답 구조에 따라 코드를 수정해야 할 수 있습니다.
- 네트워크 연결, 방화벽, VPN 등 환경에 따라 API 호출이 제한될 수 있습니다.

