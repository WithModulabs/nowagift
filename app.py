import streamlit as st
import time
import os
import uuid
from typing import TypedDict, List, Dict
from dotenv import load_dotenv
from PIL import Image
from moviepy import (
    ImageClip,
    VideoFileClip,
    AudioFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips
)
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END

from apiHeygen import HeygenAPI
from apiKlingAI import KlingAIAPI
import requests
import base64

# 환경변수 로드
load_dotenv()

# --- 1. 기본 설정 및 API 키 입력 ---
# .env 파일에서 OpenRouter API 키 로드

openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_api_key:
    os.environ["OPENAI_API_KEY"] = openrouter_api_key
else:
    raise RuntimeError(
        "Missing OPENROUTER_API_KEY. Set it in your environment or .env file (OPENROUTER_API_KEY=...)."
    )

# 임시 파일들을 저장할 디렉토리 생성
if not os.path.exists("temp"):
    os.makedirs("temp")

# --- 2. LangGraph 상태 정의 ---
# 각 에이전트가 작업 내용을 공유하는 데이터 구조
class AgentState(TypedDict):
    theme: str
    script: str
    image_paths: List[str]
    audio_path: str
    total_duration: int
    storyboard: List[Dict]  # 시나리오 작가의 결과물 (이미지, 텍스트, 길이 등)
    subtitle_clips: List[VideoFileClip]  # 자막이 포함된 클립 리스트
    final_video_path: str   # 최종 제작자의 결과물 (완성된 영상 경로)
    error_message: str      # 오류 발생 시 메시지 저장
    generated_video_paths: List[str]  # image_video_generator_agent가 생성한 비디오 경로들

# --- 3. 에이전트 및 도구(Tool) 정의 ---
    """
    각 에이전트는 특정 작업을 수행하며, 상태 업데이트
    - 3.1. 시나리오 작가 에이전트: 스크립트와 이미지 개수를 기반으로 스토리보드 생성
    - 3.2. 이미지-비디오 생성 에이전트: 사용자 이미지를 바탕으로 모션 비디오 생성
    - 3.3. 자막 생성 에이전트: 스크립트를 바탕으로 자막 영상 생성
    - 3.4. 최종 제작자 에이전트: 기존 영상과 자막 영상을 결합하여 최종 영상 제작
    """

# 3.1. 시나리오 작가 에이전트 (Scenario Writer Agent)
def scenario_writer_agent(state: AgentState):
    """스크립트와 이미지 개수를 기반으로 스토리보드를 생성합니다."""
    st.write("### 🤵 시나리오 작가 에이전트")
    st.info("입력된 스크립트와 사진들을 바탕으로 영상의 전체 흐름을 기획하고 있습니다...")

    theme = state["theme"]
    script = state["script"]
    num_images = len(state["image_paths"])
    total_duration = state["total_duration"]

    # LLM 모델 정의
    llm = ChatOpenAI(
        model="openai/gpt-5-nano",
        temperature=0.5,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": os.getenv("YOUR_SITE_URL", ""),
            "X-Title": os.getenv("YOUR_SITE_NAME", ""),
        }
    )

    # LLM에게 전달할 프롬프트 템플릿
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """당신은 감동적인 추모 영상을 위한 시나리오 작가입니다.
                사용자의 7개 장면으로 구성된 스크립트와 이미지를 바탕으로, 각 장면의 내용과 길이를 JSON 형식의 스토리보드(storyboard)로 만들어야 합니다.
                
                사용자의 스크립트는 기본적으로 7개로 구성되어 있습니다:
                1. "내가 가장 행복했을 때는"
                2. 사용자 자유 입력
                3. 사용자 자유 입력  
                4. "여보,"
                5. 사용자 자유 입력
                6. 사용자 자유 입력
                7. "지금, 선물"
                
                - 전체 영상 길이는 반드시 {total_duration}초가 되어야 합니다.
                - 각 장면은 10초, 10초, 10초, 5초, 10초, 10초, 12초로 구성됩니다.
                - 각 장면(scene)은 'image_index', 'duration', 'subtitle' 키만 가져야 합니다.
                - 'image_index'는 순서대로 1, 2, 3, 4, 5, 6, 7로 구성됩니다.
                - 'duration'은 해당 장면의 초 단위 길이입니다. 모든 duration의 합은 {total_duration}이 되어야 합니다.
                - narration, visual_cue, music_cue 등의 추가 필드는 절대 생성하지 마세요.
                - 테마 '{theme}'의 분위기를 반영해주세요.
                - 최종 출력은 오직 JSON 객체만 있어야 합니다.
                """,
            ),
            (
                "human",
                "사용자 스크립트: {script}\n"
            ),
        ]
    )
    
    # JSON 출력을 위한 파서
    parser = JsonOutputParser()

    # 체인 구성
    chain = prompt | llm | parser

    try:
        storyboard_data = chain.invoke({
            "total_duration": total_duration,
            "num_images": num_images,
            "theme": theme,
            "script": script,
        })
        
        # storyboard_data가 None인지 확인
        if storyboard_data is None:
            error_msg = "OpenAI API로부터 응답을 받지 못했습니다. API 키를 확인해주세요."
            st.error(error_msg)
            return {"error_message": error_msg}
        
        # 'storyboard' 키가 있는지 확인하고 추출
        if isinstance(storyboard_data, dict) and 'storyboard' in storyboard_data:
            storyboard = storyboard_data['storyboard']
        elif isinstance(storyboard_data, dict) and 'scenes' in storyboard_data:
            # 'scenes' 키가 있는 경우도 처리
            storyboard = storyboard_data['scenes']
        elif isinstance(storyboard_data, list):
            # 직접 리스트로 반환된 경우
            storyboard = storyboard_data
        else:
            # 딕셔너리이지만 storyboard나 scenes 키가 없는 경우, 값들을 리스트로 변환 시도
            if isinstance(storyboard_data, dict):
                # 딕셔너리의 값들이 scene 객체들인지 확인
                values = list(storyboard_data.values())
                if values and all(isinstance(v, dict) and 'image_index' in v for v in values):
                    storyboard = values
                else:
                    storyboard = storyboard_data
            else:
                storyboard = storyboard_data

        # storyboard가 리스트인지 최종 확인
        if not isinstance(storyboard, list):
            error_msg = f"스토리보드를 리스트 형태로 변환할 수 없습니다. 타입: {type(storyboard)}, 내용: {storyboard}"
            st.error(error_msg)
            return {"error_message": error_msg}

        # storyboard duration 지정
        durations = [10, 10, 10, 5, 10, 10, 12]
        if len(storyboard) == len(durations):
            for i in range(len(storyboard)):
                if isinstance(storyboard[i], dict):
                    storyboard[i]['duration'] = durations[i]
        
        st.success("스토리보드 기획 완료!")
        # 디버깅을 위해 스토리보드 출력
        with st.expander("생성된 스토리보드 보기"):
            st.json(storyboard)

        return {"storyboard": storyboard}
    
    except Exception as e:
        error_msg = f"시나리오 작성 중 오류 발생: {e}"
        st.error(error_msg)
        return {"error_message": error_msg}

# 3.2. 이미지-비디오 생성 에이전트 (Image Video Generator Agent) 
def image_video_generator_agent(state: AgentState):
    """사용자 이미지를 바탕으로 HeyGen과 KlingAI를 사용해 모션 비디오를 생성합니다."""
    st.write("### 🎨 이미지-비디오 생성 에이전트")
    st.info("업로드된 사진들을 바탕으로 움직이는 영상을 생성하고 있습니다...")
    
    image_paths = state.get("image_paths")
    theme = state.get("theme")
    
    if not image_paths:
        error_msg = "이미지-비디오 생성에 필요한 사진이 없습니다."
        st.error(error_msg)
        return {"error_message": error_msg}
    
    heygen_api_key = os.getenv("HEYGEN_API_KEY")
    kling_ak = os.getenv("AK")
    kling_sk = os.getenv("SK")
    
    use_original_images = False
    if not heygen_api_key:
        st.warning("HeyGen API 키가 설정되지 않았습니다. 원본 이미지를 사용합니다.")
        use_original_images = True
    elif not kling_ak or not kling_sk:
        st.warning("KlingAI API 키가 설정되지 않았습니다. 원본 이미지를 사용합니다.")
        use_original_images = True
    
    generated_video_paths = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, image_path in enumerate(image_paths):
        try:
            # 진행률 업데이트
            progress = (idx + 1) / len(image_paths)
            progress_bar.progress(progress)
            status_text.text(f"이미지 {idx + 1}/{len(image_paths)} 처리 중...")
            
            enhanced_image_path = image_path  # 기본값으로 원본 이미지 설정
            video_creation_success = False
            
            if not use_original_images:
                try:
                    st.write(f"HeyGen으로 이미지 {idx + 1} 처리 중...")
                    heygen = HeygenAPI(heygen_api_key)
                    heygen_result = heygen.generate_avatar_photo(
                        image_path=image_path,
                        name=f"Person_{idx+1}",
                        age="Late Middle Age",
                        gender="Person",
                        ethnicity="East Asian",
                        orientation="horizontal",
                        pose="half_body",
                        style="Realistic",
                        appearance="A headshot of a person with a gentle smile. Clean white background. Professional and warm expression."
                    )
                    
                    if heygen_result.get("data") and heygen_result["data"].get("generation_id"):
                        generation_id = heygen_result["data"]["generation_id"]
                        max_wait_time = 300  # 5분 대기
                        wait_time = 0
                        
                        while wait_time < max_wait_time:
                            status = heygen.check_generation_status(generation_id)
                            if status.get("data") and status["data"].get("status") == "success":
                                image_urls = status["data"].get("image_url_list", [])
                                if image_urls:
                                    img_resp = requests.get(image_urls[0])
                                    if img_resp.status_code == 200:
                                        enhanced_image_path = f"temp/enhanced_image_{idx+1}_{uuid.uuid4()}.jpg"
                                        with open(enhanced_image_path, "wb") as f:
                                            f.write(img_resp.content)
                                        st.success(f"HeyGen 이미지 {idx + 1} 생성 완료")
                                        break
                            time.sleep(5)  
                            wait_time += 5
                        else:
                            st.warning(f"HeyGen 이미지 {idx + 1} 생성 시간 초과, 원본 이미지 사용")
                    
                    st.write(f"KlingAI로 비디오 {idx + 1} 생성 중...")
                    
                    with open(enhanced_image_path, "rb") as img_file:
                        img_base64 = base64.b64encode(img_file.read()).decode("utf-8")
                    
                    klingai = KlingAIAPI(kling_ak, kling_sk)
                    video_data = {
                        "model_name": "kling-v2-1",
                        "mode": "pro",
                        "duration": "10",
                        "image": img_base64,  
                        "prompt": f"Create a gentle, moving video from this memorial photo. {theme} style. Soft, warm lighting with subtle camera movement. The person in the photo should have a gentle, peaceful expression.",
                        "cfg_scale": 0.5,
                    }
                    
                    init_response = klingai.generate_video(video_data)
                    task_data = init_response.get("data", {})
                    task_id = task_data.get("task_id")
                    
                    if not task_id:
                        st.warning(f"KlingAI 비디오 {idx + 1} 생성 요청 실패, 정적 이미지 사용")
                    else:
                        st.write(f"KlingAI 작업 ID: {task_id}")
                        
                        max_wait = 600  # 최대 대기 시간 (10분)
                        interval = 15   # 폴링 간격 (15초)
                        start_time = time.time()
                        
                        while time.time() - start_time < max_wait:
                            status_response = klingai.check_task_status(task_id)
                            poll_data = status_response.get("data", {})
                            poll_status = poll_data.get("task_status")
                            
                            st.write(f"KlingAI 상태: {poll_status}")
                            
                            if poll_status == "succeed":
                                videos = poll_data.get("task_result", {}).get("videos", [])
                                if videos:
                                    video_url = videos[0].get("url")
                                    st.success(f"KlingAI 비디오 {idx + 1} 생성 성공!")
                                    
                                    video_response = requests.get(video_url, stream=True)
                                    video_response.raise_for_status()
                                    
                                    video_path = f"temp/generated_video_{idx+1}_{uuid.uuid4()}.mp4"
                                    with open(video_path, "wb") as f:
                                        for chunk in video_response.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                    
                                    generated_video_paths.append(video_path)
                                    st.success(f"KlingAI 비디오 {idx + 1} 다운로드 완료")
                                    video_creation_success = True
                                    break
                                else:
                                    st.warning(f"KlingAI 비디오 {idx + 1} 정보가 응답에 포함되어 있지 않습니다.")
                                    break
                            
                            elif poll_status == "failed":
                                fail_msg = poll_data.get("task_status_msg", "실패 사유 알 수 없음")
                                if "risk control" in fail_msg.lower():
                                    st.info(f"KlingAI 콘텐츠 정책으로 인해 비디오 {idx + 1} 생성이 제한되었습니다. 정적 이미지를 사용합니다.")
                                else:
                                    st.warning(f"KlingAI 비디오 {idx + 1} 생성 실패: {fail_msg}")
                                break
                                
                            time.sleep(interval)
                        else:
                            st.warning(f"KlingAI 비디오 {idx + 1} 생성 시간 초과, 정적 이미지 사용")
                
                except Exception as api_error:
                    error_msg = str(api_error)
                    if "insufficient_quota" in error_msg or "402" in error_msg:
                        st.warning(f"API 할당량이 부족합니다. 원본 이미지를 사용합니다.")
                        use_original_images = True
                    else:
                        st.warning(f"API 오류 발생: {error_msg}. 원본 이미지를 사용합니다.")
            
            if not video_creation_success or use_original_images:
                st.write(f"정적 비디오 {idx + 1} 생성 중...")
                try:
                    video_clip = ImageClip(enhanced_image_path).with_duration(10)
                    video_path = f"temp/static_video_{idx+1}_{uuid.uuid4()}.mp4"
                    video_clip.write_videofile(video_path, codec="libx264", fps=24)
                    generated_video_paths.append(video_path)
                    st.success(f"정적 비디오 {idx + 1} 생성 완료")
                except Exception as video_error:
                    st.error(f"비디오 생성 중 오류 발생: {video_error}")
                    try:
                        video_clip = ImageClip(image_path).with_duration(10)
                        video_path = f"temp/fallback_video_{idx+1}_{uuid.uuid4()}.mp4"
                        video_clip.write_videofile(video_path, codec="libx264", fps=24)
                        generated_video_paths.append(video_path)
                        st.warning(f"원본 이미지로 비디오 {idx + 1} 생성 완료")
                    except Exception as final_error:
                        error_msg = f"이미지 {idx + 1} 처리 중 치명적 오류 발생: {final_error}"
                        return {"error_message": error_msg}
            
        except Exception as e:
            st.error(f"이미지 {idx + 1} 처리 중 오류 발생: {e}")
            try:
                video_clip = ImageClip(image_path).with_duration(10)
                video_path = f"temp/fallback_video_{idx+1}_{uuid.uuid4()}.mp4"
                video_clip.write_videofile(video_path, codec="libx264", fps=24)
                generated_video_paths.append(video_path)
                st.warning(f"오류 복구: 원본 이미지로 비디오 {idx + 1} 생성 완료")
            except:
                error_msg = f"이미지 {idx + 1} 처리 중 치명적 오류 발생: {e}"
                return {"error_message": error_msg}
    
    if not generated_video_paths:
        error_msg = "생성된 비디오가 하나도 없습니다."
        st.error(error_msg)
        return {"error_message": error_msg}
    
    if use_original_images:
        st.success(f"총 {len(generated_video_paths)}개의 정적 비디오 생성 완료! (원본 이미지 사용)")
    else:
        st.success(f"총 {len(generated_video_paths)}개의 비디오 생성 완료!")
    
    return {"generated_video_paths": generated_video_paths}

# 3.3. 자막 생성 에이전트 (Subtitle Creator Agent) 
def subtitle_creator_agent(state: AgentState):
    """스크립트를 바탕으로 투명한 배경의 자막 영상을 생성합니다."""
    st.write("### 📝 자막 생성 에이전트")
    st.info("입력된 스크립트를 바탕으로 각 장면에 들어갈 자막 영상을 만들고 있습니다...")
    
    script_lines = state.get("script").split("\n")
    storyboard = state.get("storyboard")
    
    if not storyboard or not script_lines:
        error_msg = "자막 생성에 필요한 정보(스토리보드, 스크립트)가 부족합니다."
        st.error(error_msg)
        return {"error_message": error_msg}
    
    # 디버깅을 위해 storyboard 타입과 내용 확인
    st.write(f"Storyboard type in subtitle creator: {type(storyboard)}")
    st.write(f"Storyboard content: {storyboard}")
    
    # storyboard가 리스트가 아닌 경우 처리
    if not isinstance(storyboard, list):
        error_msg = f"스토리보드가 예상된 리스트 형식이 아닙니다. 현재 타입: {type(storyboard)}"
        st.error(error_msg)
        return {"error_message": error_msg}

    # 폰트 경로 설정 
    font_path = "resources/font/movie-font.ttf"
    if not os.path.exists(font_path):
        error_msg = f"지정된 폰트 파일을 찾을 수 없습니다: {font_path}"
        st.error(error_msg)
        return {"error_message": error_msg}
    
    subtitle_clips = []
    
    for idx, scene in enumerate(storyboard):
        try:
            if (idx + 1) in [1, 4, 7]:
                subtitle_clips.append(None)
                continue
            
            text = script_lines[idx].strip()
            
            if not isinstance(scene, dict):
                st.error(f"장면 {idx+1}이 딕셔너리가 아닙니다. 타입: {type(scene)}, 내용: {scene}")
                continue
            
            if 'duration' not in scene:
                st.error(f"장면 {idx+1}에 'duration' 키가 없습니다. 키들: {list(scene.keys())}")
                continue
                
            duration = scene['duration']
            
            # 기본 TextClip 생성
            main_text_clip = TextClip(
                text=text,
                font_size=40,
                color='white',
                font=font_path,
                transparent=True
            ).with_duration(duration).with_position(("center", 810), relative=False)

            # 그림자 효과를 위한 TextClip 생성
            shadow_text_clip = TextClip(
                text=text,
                font_size=40,
                color='black',
                font=font_path,
                transparent=True
            ).with_duration(duration).with_position(("center", 815), relative=False)  
            
            # 두 클립을 합쳐서 하나의 자막 클립으로 만듦
            subtitle_clip = CompositeVideoClip([shadow_text_clip, main_text_clip], size=(1920, 1080))
        
            subtitle_clips.append(subtitle_clip)
            
        except IndexError:
            st.warning(f"스크립트 문항이 부족합니다. 장면 {idx+1}의 자막은 건너뜁니다.")
            subtitle_clips.append(None)
            continue
        except Exception as e:
            st.error(f"자막 생성 중 오류 발생: {e}")
            return {"error_message": f"자막 생성 중 오류 발생: {e}"}

    if not any(subtitle_clips): 
        error_msg = "자막을 구성할 장면이 하나도 없습니다."
        st.error(error_msg)
        return {"error_message": error_msg}
    
    st.success("자막 클립 생성 완료!")
    
    # 각 장면별로 생성된 클립들의 리스트를 반환
    return {"subtitle_clips": subtitle_clips}

# 3.4. 최종 제작자 에이전트 (Final Producer Agent) 
def final_producer_agent(state: AgentState):
    """기존 영상과 자막 영상을 결합하여 최종 영상을 제작합니다."""
    st.write("### 🎬 최종 제작자 에이전트")
    st.info("기획된 스토리보드에 따라 사진, 자막, 음성을 합쳐 최종 영상을 만들고 있습니다...")
    
    storyboard = state.get("storyboard")
    image_paths = state.get("image_paths")
    audio_path = state.get("audio_path")
    subtitle_clips = state.get("subtitle_clips")
    generated_video_paths = state.get("generated_video_paths", [])
    
    # 테마별 효과 설정
    # 이 부분을 확장하여 더 다양한 효과를 추가할 수 있습니다.
    def apply_theme_effects(clip, duration):
        # Effects 사용을 제거하고 기본 클립 반환
        return clip

    # 디버깅을 위해 storyboard 타입과 내용 확인
    st.write(f"Storyboard type: {type(storyboard)}")
    st.write(f"Storyboard content: {storyboard}")
    
    # storyboard가 문자열인 경우 JSON으로 파싱
    if isinstance(storyboard, str):
        import json
        try:
            storyboard = json.loads(storyboard)
        except json.JSONDecodeError:
            st.error("스토리보드 파싱 오류: JSON 형식이 올바르지 않습니다.")
            return {"error_message": "스토리보드 파싱 오류"}
    
    # 각 장면별로 기본 영상과 자막을 합성할 리스트
    combined_clips = []
    
    # 진행률 및 시간 표시를 위한 설정
    total_scenes = len(storyboard)
    start_time = time.time()

    # 진행률 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    time_text = st.empty()

    # 예상 시간 계산 (장면당 평균 3초로 가정)
    estimated_total_time = total_scenes * 3

    for scene_idx, scene in enumerate(storyboard):
        try:
            # 먼저 장면 데이터 추출
            img_index = scene['image_index']
            duration = scene['duration']

            # 진행률 업데이트
            progress = (scene_idx + 1) / total_scenes
            progress_bar.progress(progress)

            # 상태 텍스트 업데이트
            status_text.text(f"장면 {scene_idx + 1}/{total_scenes} 처리 중...")

            # 경과 시간 및 예상 시간 계산
            elapsed_time = time.time() - start_time
            if scene_idx > 0:
                avg_time_per_scene = elapsed_time / scene_idx
                remaining_scenes = total_scenes - scene_idx
                estimated_remaining_time = avg_time_per_scene * remaining_scenes

                time_text.text(f"⏱️ 경과 시간: {elapsed_time:.0f}초 | 예상 남은 시간: {estimated_remaining_time:.0f}초")
            else:
                time_text.text(f"⏱️ 예상 소요 시간: {estimated_total_time}초")

            video_clip = None
            
            if img_index == 1:
                video_clip = VideoFileClip("resources/theme/t01.mp4").with_duration(duration)
            elif img_index == 2:
                if len(generated_video_paths) > 0 and os.path.exists(generated_video_paths[0]):
                    video_clip = VideoFileClip(generated_video_paths[0]).with_duration(duration)
                elif len(image_paths) > 0:
                    # 백업: 원본 이미지 사용
                    video_clip = ImageClip(image_paths[0]).with_duration(duration)
                else:
                    st.warning("장면 2에 필요한 사진이 없어 기본 클립을 사용합니다.")
                    video_clip = VideoFileClip("resources/theme/t01.mp4").with_duration(duration)
            elif img_index == 3:
                if len(generated_video_paths) > 1 and os.path.exists(generated_video_paths[1]):
                    video_clip = VideoFileClip(generated_video_paths[1]).with_duration(duration)
                elif len(image_paths) > 1:
                    # 백업: 원본 이미지 사용
                    video_clip = ImageClip(image_paths[1]).with_duration(duration)
                else:
                    st.warning("장면 3에 필요한 사진이 없어 기본 클립을 사용합니다.")
                    video_clip = VideoFileClip("resources/theme/t01.mp4").with_duration(duration)
            elif img_index == 4:
                video_clip = VideoFileClip("resources/theme/t04.mp4").with_duration(duration)
            elif img_index == 5:
                if len(generated_video_paths) > 2 and os.path.exists(generated_video_paths[2]):
                    video_clip = VideoFileClip(generated_video_paths[2]).with_duration(duration)
                elif len(image_paths) > 2:
                    # 백업: 원본 이미지 사용
                    video_clip = ImageClip(image_paths[2]).with_duration(duration)
                else:
                    st.warning("장면 5에 필요한 사진이 없어 기본 클립을 사용합니다.")
                    video_clip = VideoFileClip("resources/theme/t01.mp4").with_duration(duration)
            elif img_index == 6:
                if len(generated_video_paths) > 3 and os.path.exists(generated_video_paths[3]):
                    video_clip = VideoFileClip(generated_video_paths[3]).with_duration(duration)
                elif len(image_paths) > 3:
                    # 백업: 원본 이미지 사용
                    video_clip = ImageClip(image_paths[3]).with_duration(duration)
                else:
                    st.warning("장면 6에 필요한 사진이 없어 기본 클립을 사용합니다.")
                    video_clip = VideoFileClip("resources/theme/t01.mp4").with_duration(duration)
            elif img_index == 7:
                video_clip = VideoFileClip("resources/theme/ending.mp4").with_duration(duration)
            else:
                st.warning(f"알 수 없는 이미지 인덱스 {img_index}. 기본 클립을 사용합니다.")
                video_clip = VideoFileClip("resources/theme/t01.mp4").with_duration(duration)
            
            if video_clip:
                video_clip = video_clip.resized(height=1080)
            
            final_scene_clip = video_clip
            
            # 삭제: 1, 4, 7번째 자막이 None이므로, 해당 클립이 있을 때만 합성
            if subtitle_clips and len(subtitle_clips) > scene_idx and subtitle_clips[scene_idx] is not None:
                current_subtitle_clip = subtitle_clips[scene_idx]
                final_scene_clip = CompositeVideoClip([video_clip, current_subtitle_clip])
            
            if final_scene_clip:
                combined_clips.append(final_scene_clip)

        # 테마 적용
        #video_clip = apply_theme_effects(video_clip, duration)                
        #clips.append(video_clip)
        
        except Exception as e:
            st.error(f"장면 생성 중 오류 발생: {e}")
            return {"error_message": f"장면 생성 중 오류 발생: {e}"}

    if not combined_clips:
        error_msg = "영상을 구성할 장면이 하나도 없습니다."
        st.error(error_msg)
        return {"error_message": error_msg}

    # 모든 영상 클립을 하나로 연결
    final_video_clip = concatenate_videoclips(combined_clips, method="compose")

    # 백그라운드 음악 추가
    background_music_path = "resources/music/m0.mp3"
    if os.path.exists(background_music_path):
        background_music = AudioFileClip(background_music_path)

        # 배경음악을 영상 길이에 맞게 조정
        if background_music.duration < final_video_clip.duration:
            # 음악이 짧으면 반복
            loops_needed = int(final_video_clip.duration / background_music.duration) + 1
            background_music = background_music.loop(loops_needed)

        # 음악을 영상 길이에 맞게 자르기
        background_music = background_music.subclipped(0, final_video_clip.duration)

        # 배경음악 볼륨 조절 - MoviePy 버전 호환성을 위해 간단하게 처리
        background_music = background_music.with_fps(22050)
        # 볼륨 조절은 오디오 믹싱 시 CompositeAudioClip에서 처리

        if audio_path:
            # 사용자 음성이 있으면 믹싱
            user_audio = AudioFileClip(audio_path)
            if user_audio.duration > final_video_clip.duration:
                user_audio = user_audio.subclipped(0, final_video_clip.duration)

            # 두 오디오를 합성 (배경음악 + 사용자 음성)
            from moviepy import CompositeAudioClip
            # 배경음악과 사용자 음성을 믹싱 (배경음악은 자동으로 낮은 볼륨)
            mixed_audio = CompositeAudioClip([background_music, user_audio])
            final_video_clip = final_video_clip.with_audio(mixed_audio)
        else:
            # 사용자 음성이 없으면 배경음악만
            final_video_clip = final_video_clip.with_audio(background_music)
    else:
        # 배경음악 파일이 없는 경우 기존 로직
        if audio_path:
            audio_clip = AudioFileClip(audio_path)
            if audio_clip.duration > final_video_clip.duration:
                audio_clip = audio_clip.subclipped(0, final_video_clip.duration)
            final_video_clip = final_video_clip.with_audio(audio_clip)

    output_filename = f"temp/final_video_{uuid.uuid4()}.mp4"
    final_video_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24)
    
    st.success("영상 제작 완료!")
    return {"final_video_path": output_filename}

# --- 4. LangGraph 워크플로우 구성 ---
workflow = StateGraph(AgentState)

workflow.add_node("scenario_writer", scenario_writer_agent)
workflow.add_node("image_video_generator", image_video_generator_agent)  
workflow.add_node("subtitle_creator", subtitle_creator_agent)
workflow.add_node("final_producer", final_producer_agent)

workflow.set_entry_point("scenario_writer")
workflow.add_edge("scenario_writer", "image_video_generator")  
workflow.add_edge("image_video_generator", "subtitle_creator") 
workflow.add_edge("subtitle_creator", "final_producer") 
workflow.add_edge("final_producer", END) 

# 그래프 컴파일
app = workflow.compile()

# --- 5. Streamlit UI 구성 ---
st.set_page_config(page_title="🕊️ 추모 영상 제작 에이전트", layout="wide")

st.title("🕊️ 추모 영상 제작 에이전트")
st.markdown("고인을 기리는 소중한 마음을 담아, 세상에 하나뿐인 영상을 만들어 드립니다.")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. 영상 정보 입력")
    
    theme = st.selectbox(
        "영상 테마 선택",
        ["따뜻한 추억 (Warm Memories)", "차분한 회상 (Calm Reflection)", "삶의 축하 (Celebrating a Life)"],
        help="영상 전체의 분위기를 결정합니다."
    )

    st.subheader("영상에 담을 글 입력 (7개 문항)")
    
    # 7개의 고정/자유 입력 필드
    text_inputs = []
    
    # 첫 번째 필드 (고정 - 입력 필드 없음)
    st.write("**장면 #1. 내가 가장 행복했을 때는**")
    text_inputs.append("내가 가장 행복했을 때는")
    
    # 두 번째 필드 (자유입력)
    text_inputs.append(st.text_input("**장면 #2.** 두 번째 문장", key="text2", value="내 나이 76세, 평생 공부하고 싶던, 대학교를 졸업했을 때."))
    
    # 세 번째 필드 (자유입력)
    text_inputs.append(st.text_input("**장면 #3.** 세 번째 문장", key="text3", value="응원해 준, 우리 딸 많이 사랑해"))
    
    # 네 번째 필드 (고정 - 입력 필드 없음)
    st.write("**장면 #4. 여보,**")
    text_inputs.append("여보,")
    
    # 다섯 번째 필드 (자유입력)
    text_inputs.append(st.text_input("**장면 #5.** 다섯 번째 문장", key="text5", value="평생 나와 살면서 고생 많았어"))
    
    # 여섯 번째 필드 (자유입력)
    text_inputs.append(st.text_input("**장면 #6.** 여섯 번째 문장", key="text6", value="항상 고맙고, 즐겁고 행복한 삶을 살았으면 좋겠다. 고맙다."))
    
    # 일곱 번째 필드 (고정 - 입력 필드 없음)
    st.write("**장면 #7. 지금, 선물**")
    text_inputs.append("지금, 선물")
    
    # 전체 텍스트 조합
    script = "\n".join([text for text in text_inputs if text.strip()])

    st.subheader("사진 업로드 (4장)")
    uploaded_images = []
    
    # 1번째 이미지 업로드 필드
    st.write("**장면 #2 사진**")
    col_upload1, col_thumb1 = st.columns([2, 1])
    
    with col_upload1:
        img1 = st.file_uploader(
            "장면 #2 사진 선택",
            type=["jpg", "jpeg", "png"],
            key="image_1",
            help="고화질 사진을 선택해주세요."
        )
    
    with col_thumb1:
        if img1 is not None:
            image1 = Image.open(img1)
            st.image(image1, width=100, caption="장면 #2 사진")

    # 2번째 이미지 업로드 필드
    st.write("**장면 #3 사진**")
    col_upload2, col_thumb2 = st.columns([2, 1])
    
    with col_upload2:
        img2 = st.file_uploader(
            "장면 #3 사진 선택",
            type=["jpg", "jpeg", "png"],
            key="image_2",
            help="고화질 사진을 선택해주세요."
        )
    
    with col_thumb2:
        if img2 is not None:
            image2 = Image.open(img2)
            st.image(image2, width=100, caption="장면 #3 사진")

    # 3번째 이미지 업로드 필드
    st.write("**장면 #5 사진**")
    col_upload3, col_thumb3 = st.columns([2, 1])
    
    with col_upload3:
        img3 = st.file_uploader(
            "장면 #5 사진 선택",
            type=["jpg", "jpeg", "png"],
            key="image_3",
            help="고화질 사진을 선택해주세요."
        )
    
    with col_thumb3:
        if img3 is not None:
            image3 = Image.open(img3)
            st.image(image3, width=100, caption="장면 #5 사진")
    
    # 4번째 이미지 업로드 필드
    st.write("**장면 #6 사진**")
    col_upload4, col_thumb4 = st.columns([2, 1])
    
    with col_upload4:
        img4 = st.file_uploader(
            "장면 #6 사진 선택",
            type=["jpg", "jpeg", "png"],
            key="image_4",
            help="고화질 사진을 선택해주세요."
        )
    
    with col_thumb4:
        if img4 is not None:
            image4 = Image.open(img4)
            st.image(image4, width=100, caption="장면 #6 사진")
    
    # 업로드된 이미지들을 리스트에 추가 (None이 아닌 것만)
    for img in [img1, img2, img3, img4]:
        if img is not None:
            uploaded_images.append(img)

    uploaded_audio = st.file_uploader(
        "음성 파일 업로드",
        type=["mp3", "wav", "m4a"],
        help="영상 전체에 사용될 음원 파일입니다. 70초 이하 길이의 파일을 권장합니다."
    )

with col2:
    st.subheader("2. 영상 생성 및 확인")
    
    if st.button("🎥 영상 제작 시작하기", type="primary"):
        # 입력 값 검증
        validation_errors = []
        # 최소 3개 이상의 필드가 입력되었는지 확인
        filled_inputs = [text for text in text_inputs if len(text.strip()) > 0]
        if len(filled_inputs) < 3:
            validation_errors.append("최소 3개 이상의 문항을 입력해주세요.")
        #if not uploaded_images:
        #    validation_errors.append("사진을 업로드해주세요.")
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        elif not os.getenv("OPENAI_API_KEY"):
            st.error(".env 파일에 OPENAI_API_KEY를 설정해주세요.")
        else:
            with st.spinner("AI 에이전트들이 영상 제작을 시작합니다... 잠시만 기다려주세요."):
                # 1. 임시 파일 저장
                temp_image_paths = []
                for img_file in uploaded_images:
                    img = Image.open(img_file)
                    file_path = f"temp/{uuid.uuid4()}.png"
                    img.save(file_path)
                    temp_image_paths.append(file_path)

                temp_audio_path = None
                if uploaded_audio:
                    temp_audio_path = f"temp/{uuid.uuid4()}.mp3"
                    with open(temp_audio_path, "wb") as f:
                        f.write(uploaded_audio.getbuffer())

                # 2. 에이전트 초기 상태 설정
                initial_state = AgentState(
                    theme=theme,
                    script=script,
                    image_paths=temp_image_paths,
                    audio_path=temp_audio_path,
                    total_duration=67, # 총 영상 길이 고정
                    storyboard=None,
                    final_video_path=None,
                    error_message=None,
                    subtitle_clips=[],
                    generated_video_paths=[] 
                )
                
                # 3. LangGraph 실행
                final_state = app.invoke(initial_state)

                # 4. 결과 처리
                if final_state.get("error_message"):
                    st.error(f"오류가 발생했습니다: {final_state['error_message']}")
                else:
                    video_path = final_state.get("final_video_path")
                    
                    if video_path and os.path.exists(video_path):
                        st.subheader("✨ 영상이 완성되었습니다 ✨")
                        st.video(video_path)
                        
                        with open(video_path, "rb") as file:
                            st.download_button(
                                label="영상 파일 다운로드",
                                data=file,
                                file_name="memorial_video.mp4",
                                mime="video/mp4"
                            )
                            
                        st.markdown("---")
                        if st.button("임시 파일 정리하기", help="다운로드 후 이 버튼을 눌러 임시 파일을 삭제하세요."):
                            if os.path.exists(video_path): os.remove(video_path)
                            for path in temp_image_paths:
                                if os.path.exists(path): os.remove(path)
                            generated_videos = final_state.get("generated_video_paths", [])
                            for video_path in generated_videos:
                                if os.path.exists(video_path): os.remove(video_path)
                            if temp_audio_path and os.path.exists(temp_audio_path) and temp_audio_path != "resources/music/m0.mp3":
                                 os.remove(temp_audio_path)
                            st.success("임시 파일이 성공적으로 삭제되었습니다.")

                    else:
                        st.error("알 수 없는 오류로 영상 파일을 찾을 수 없습니다.")

# --- UI 하단 설명 추가 ---
st.markdown("---")