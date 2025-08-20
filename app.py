import streamlit as st
import os
import uuid
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
    vfx
)
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict
import json
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# --- 1. 기본 설정 및 API 키 입력 ---
# .env 파일에서 OpenAI API 키 로드
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    os.environ["OPENAI_API_KEY"] = openai_api_key

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
    final_video_path: str   # 최종 제작자의 결과물 (완성된 영상 경로)
    error_message: str      # 오류 발생 시 메시지 저장

# --- 3. 텍스트 오버레이 함수 ---
def add_text_to_image(image_path, text, output_path):
    """이미지에 텍스트를 추가하여 새로운 이미지를 생성합니다."""
    try:
        # 이미지 열기
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        # 폰트 설정 (시스템 기본 폰트 사용)
        try:
            # Windows 한글 폰트 시도
            font = ImageFont.truetype("malgun.ttf", 40)
        except:
            try:
                # 영문 폰트 시도
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                # 기본 폰트 사용
                font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 이미지 크기
        img_width, img_height = img.size
        
        # 텍스트 위치 (하단 중앙)
        x = (img_width - text_width) // 2
        y = img_height - text_height - 50  # 하단에서 50px 위
        
        # 텍스트 배경 (검은색 반투명)
        padding = 10
        background_bbox = [
            x - padding, 
            y - padding, 
            x + text_width + padding, 
            y + text_height + padding
        ]
        
        # 반투명 배경을 위한 오버레이 이미지
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(background_bbox, fill=(0, 0, 0, 128))
        
        # 원본 이미지를 RGBA로 변환
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 오버레이 합성
        img = Image.alpha_composite(img, overlay)
        
        # 텍스트 그리기
        draw = ImageDraw.Draw(img)
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        # RGB로 변환 후 저장
        img = img.convert('RGB')
        img.save(output_path)
        return output_path
        
    except Exception as e:
        st.error(f"텍스트 오버레이 생성 중 오류: {e}")
        return image_path

# --- 4. 에이전트 및 도구(Tool) 정의 ---

# 3.1. 시나리오 작가 에이전트 (Scenario Writer Agent)
def scenario_writer_agent(state: AgentState):
    """스크립트와 이미지 개수를 기반으로 70초 분량의 스토리보드를 생성합니다."""
    st.write("### 🤵 시나리오 작가 에이전트")
    st.info("입력된 스크립트와 사진들을 바탕으로 영상의 전체 흐름을 기획하고 있습니다...")

    theme = state["theme"]
    script = state["script"]
    num_images = len(state["image_paths"])
    total_duration = state["total_duration"]

    # LLM 모델 정의
    llm = ChatOpenAI(model="gpt-4o", temperature=0.5)

    # LLM에게 전달할 프롬프트 템플릿
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """당신은 감동적인 추모 영상을 위한 시나리오 작가입니다.
                사용자의 7개 문항으로 구성된 스크립트와 이미지 개수를 바탕으로, 각 장면의 내용과 길이를 JSON 형식의 스토리보드(storyboard)로 만들어야 합니다.
                
                사용자의 스크립트는 7개의 문항으로 구성되어 있습니다:
                1. "내가 가장 행복했을 때는" + 사용자 입력
                2. 사용자 자유 입력
                3. 사용자 자유 입력  
                4. "여보," + 사용자 입력
                5. 사용자 자유 입력
                6. 사용자 자유 입력
                7. "지금, 선물" + 사용자 입력
                
                - 전체 영상 길이는 반드시 {total_duration}초가 되어야 합니다.
                - 이미지 개수({num_images}개)에 맞춰 각 장면의 길이를 균등하게 또는 의미에 맞게 배분해주세요.
                - 각 장면(scene)은 'image_index', 'duration', 'text_overlay' 키를 가져야 합니다.
                - 'image_index'는 0부터 시작하는 이미지 순서입니다.
                - 'duration'은 해당 장면의 초 단위 길이입니다. 모든 duration의 합은 {total_duration}이 되어야 합니다.
                - 'text_overlay'는 해당 장면에 표시될 자막입니다. 사용자의 7개 문항을 각 장면에 자연스럽게 배분하되, 문항의 순서와 의미를 고려해주세요.
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
        
        # 'storyboard' 키가 있는지 확인하고 추출
        if 'storyboard' in storyboard_data:
            storyboard = storyboard_data['storyboard']
        else: # 가끔 LLM이 최상위 키 없이 바로 리스트를 반환할 때를 대비
            storyboard = storyboard_data

        st.success("스토리보드 기획 완료!")
        # 디버깅을 위해 스토리보드 출력
        with st.expander("생성된 스토리보드 보기"):
            st.json(storyboard)

        return {"storyboard": storyboard}
    
    except Exception as e:
        error_msg = f"시나리오 작성 중 오류 발생: {e}"
        st.error(error_msg)
        return {"error_message": error_msg}


# 3.2. 최종 제작자 (Final Producer) - 영상 생성 도구
def final_producer_tool(state: AgentState):
    """스토리보드를 바탕으로 실제 영상 파일을 제작합니다."""
    st.write("### 🎬 최종 제작자 에이전트")
    st.info("기획된 스토리보드에 따라 사진, 자막, 음성을 합쳐 최종 영상을 만들고 있습니다...")
    return {"final_video_path": "ok"}
    
    storyboard = state.get("storyboard")
    image_paths = state.get("image_paths")
    audio_path = state.get("audio_path")
    total_duration = state.get("total_duration")

    if not storyboard or not image_paths or not audio_path:
        error_msg = "영상 제작에 필요한 정보(스토리보드, 이미지, 오디오)가 부족합니다."
        st.error(error_msg)
        return {"error_message": error_msg}

    clips = []
    
    # 테마별 효과 설정
    # 이 부분을 확장하여 더 다양한 효과를 추가할 수 있습니다.
    def apply_theme_effects(clip, duration):
        theme = state['theme']
        if theme == "따뜻한 추억 (Warm Memories)":
            # 1.2배로 천천히 줌 인 되는 효과
            return clip.resize(lambda t: 1 + 0.2 * t / duration).fx(vfx.fadein, 1).fx(vfx.fadeout, 1)
        elif theme == "차분한 회상 (Calm Reflection)":
            # 흑백 처리 및 페이드 효과
            return clip.fx(vfx.blackwhite).fx(vfx.fadein, 1.5).fx(vfx.fadeout, 1.5)
        else: # "삶의 축하 (Celebrating a Life)" 및 기본
            # 페이드 효과만 적용
            return clip.fx(vfx.fadein, 1).fx(vfx.fadeout, 1)


    for scene in storyboard:
        try:
            img_index = scene['image_index']
            duration = scene['duration']
            text = scene['text_overlay']
            
            # 텍스트가 추가된 이미지 생성
            text_overlay_path = f"temp/text_overlay_{uuid.uuid4()}.jpg"
            processed_image_path = add_text_to_image(image_paths[img_index], text, text_overlay_path)
            
            # 텍스트가 추가된 이미지로 클립 생성
            img_clip = ImageClip(processed_image_path).set_duration(duration)

            # 테마 적용
            video_clip = apply_theme_effects(img_clip, duration)
            clips.append(video_clip)

        except IndexError:
            st.warning(f"이미지 인덱스 {img_index}가 범위를 벗어났습니다. 이 장면은 건너뜁니다.")
            continue
        except Exception as e:
            st.error(f"장면 생성 중 오류 발생: {e}")
            return {"error_message": f"장면 생성 중 오류 발생: {e}"}

    if not clips:
        error_msg = "영상을 구성할 장면이 하나도 없습니다."
        st.error(error_msg)
        return {"error_message": error_msg}

    # 모든 영상 클립을 하나로 연결
    final_clip = concatenate_videoclips(clips, method="compose")

    # 오디오 파일 로드 및 영상 길이에 맞게 조절
    audio_clip = AudioFileClip(audio_path)
    if audio_clip.duration > total_duration:
        audio_clip = audio_clip.subclip(0, total_duration)

    # 영상에 오디오 삽입
    final_clip = final_clip.set_audio(audio_clip)

    # 최종 영상 파일로 저장
    output_filename = f"temp/final_video_{uuid.uuid4()}.mp4"
    final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24)
    
    st.success("영상 제작 완료!")
    return {"final_video_path": output_filename}


# --- 4. LangGraph 워크플로우 구성 ---
workflow = StateGraph(AgentState)

# 노드(에이전트) 추가
workflow.add_node("scenario_writer", scenario_writer_agent)
workflow.add_node("producer", final_producer_tool)

# 엣지(흐름) 연결
workflow.set_entry_point("scenario_writer")
workflow.add_edge("scenario_writer", "producer")
workflow.add_edge("producer", END)

# 그래프 컴파일
app = workflow.compile()

# --- 5. Streamlit UI 구성 ---
st.set_page_config(page_title="🕊️ 추모 영상 제작 에이전트", layout="wide")

st.title("🕊️ 70초 추모 영상 제작 에이전트")
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
    st.write("**1. 내가 가장 행복했을 때는**")
    text_inputs.append("내가 가장 행복했을 때는")
    
    # 두 번째 필드 (자유입력)
    text_inputs.append(st.text_input("**2.** 두 번째 문장", key="text2", value="내 나이 76세, 평생 공부하고 싶던, 대학교를 졸업했을 때."))
    
    # 세 번째 필드 (자유입력)
    text_inputs.append(st.text_input("**3.** 세 번째 문장", key="text3", value="응원해 준, 우리 딸 많이 사랑해"))
    
    # 네 번째 필드 (고정 - 입력 필드 없음)
    st.write("**4. 여보,**")
    text_inputs.append("여보,")
    
    # 다섯 번째 필드 (자유입력)
    text_inputs.append(st.text_input("**5.** 다섯 번째 문장", key="text5", value="평생 나와 살면서 고생 많았어"))
    
    # 여섯 번째 필드 (자유입력)
    text_inputs.append(st.text_input("**6.** 여섯 번째 문장", key="text6", value="항상 고맙고, 즐겁고 행복한 삶을 살았으면 좋겠다. 고맙다."))
    
    # 일곱 번째 필드 (고정 - 입력 필드 없음)
    st.write("**7. 지금, 선물**")
    text_inputs.append("지금, 선물")
    
    # 전체 텍스트 조합
    script = "\n".join([text for text in text_inputs if text.strip()])

    uploaded_images = st.file_uploader(
        "사진 업로드 (5장 이상 권장)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        help="고화질 사진을 시간 순서대로 선택하면 더 좋습니다."
    )

    uploaded_audio = st.file_uploader(
        "음성 파일 업로드",
        type=["mp3", "wav", "m4a"],
        help="영상 전체에 사용될 음원 파일입니다. 70초 이상 길이의 파일을 권장합니다."
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
        if not uploaded_images:
            validation_errors.append("사진을 업로드해주세요.")
        if not uploaded_audio:
            validation_errors.append("음성 파일을 업로드해주세요.")
        
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

                temp_audio_path = f"temp/{uuid.uuid4()}.mp3"
                with open(temp_audio_path, "wb") as f:
                    f.write(uploaded_audio.getbuffer())

                # 2. 에이전트 초기 상태 설정
                initial_state = AgentState(
                    theme=theme,
                    script=script,
                    image_paths=temp_image_paths,
                    audio_path=temp_audio_path,
                    total_duration=70, # 총 영상 길이 70초 고정
                    storyboard=None,
                    final_video_path=None,
                    error_message=None
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
                    else:
                        st.error("알 수 없는 오류로 영상 파일을 찾을 수 없습니다.")

                # 5. 임시 파일 정리
                for path in temp_image_paths:
                    if os.path.exists(path): os.remove(path)
                if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
                if 'video_path' in locals() and os.path.exists(video_path): 
                     os.remove(video_path)


# --- UI 하단 설명 추가 ---
st.markdown("---")