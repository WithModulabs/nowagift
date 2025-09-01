import time
import os
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types

# Load .env and get GOOGLE_API_KEY
load_dotenv()
_google_api_key = os.getenv("GOOGLE_API_KEY")
if _google_api_key:
    client = genai.Client(api_key=_google_api_key)
else:
    raise RuntimeError(
        "Missing GOOGLE_API_KEY. Set it in your environment or .env file (GOOGLE_API_KEY=...)."
    )

operation = client.models.generate_videos(
    model="veo-3.0-generate-preview",
    prompt="a close-up shot of a golden retriever playing in a field of sunflowers",
    config=types.GenerateVideosConfig(
        negative_prompt="barking, woofing",
    ),
)

# Waiting for the video(s) to be generated
while not operation.done:
    time.sleep(20)
    operation = client.operations.get(operation)

generated_video = operation.result.generated_videos[0]
client.files.download(file=generated_video.video)
generated_video.video.save("veo3_video.mp4")