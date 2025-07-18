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

## 참고
- 공식 문서의 엔드포인트, 파라미터, 응답 구조에 따라 코드를 수정해야 할 수 있습니다.
- 네트워크 연결, 방화벽, VPN 등 환경에 따라 API 호출이 제한될 수 있습니다.
