# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project that creates memorial videos using AI technologies. It integrates multiple AI services:
- **Kling AI**: For image and video generation using JWT authentication
- **HeyGen API**: For avatar photo generation 
- **OpenAI**: For content generation and script processing
- **Streamlit**: For the web application interface
- **LangGraph**: For orchestrating AI agents in video creation workflow

## Development Environment Setup

### Virtual Environment
```bash
# Create and activate virtual environment (Windows)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file in the project root with:
```
AK=your_kling_access_key
SK=your_kling_secret_key
HEYGEN_API_KEY=your_heygen_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Core Architecture

### Main Applications
- **app.py**: Streamlit web application for creating 70-second memorial videos using LangGraph agents
- **main.py**: Simple entry point script
- **apiToken.py**: Kling AI image generation with JWT authentication
- **apiVideo.py**: Kling AI video generation from images
- **apiHeygen.py**: HeyGen avatar photo generation and polling

### AI Agent Workflow (app.py)
The application uses LangGraph to orchestrate two main agents:
1. **Scenario Writer Agent**: Processes user script and creates storyboard with timing
2. **Final Producer Agent**: Combines images, audio, and text overlays into final video

### Key Dependencies
- `streamlit`: Web interface
- `langchain` + `langgraph`: AI agent orchestration
- `moviepy`: Video processing and editing
- `PIL`: Image processing
- `requests`: API calls
- `pyjwt`: JWT token generation for Kling AI
- `python-dotenv`: Environment variable management

## Common Development Commands

### Running the Applications
```bash
# Run Streamlit memorial video creator
streamlit run app.py

# Run Kling AI image generation test
python apiToken.py

# Run Kling AI video generation test  
python apiVideo.py

# Run HeyGen avatar generation test
python apiHeygen.py

# Run basic entry point
python main.py
```

### API Testing
Each API module can be run independently to test different AI services:
- Image generation via Kling AI (apiToken.py)
- Video generation via Kling AI (apiVideo.py) 
- Avatar photo generation via HeyGen (apiHeygen.py)

## Code Architecture Notes

### Authentication Patterns
- **Kling AI**: Uses JWT tokens generated from AK/SK credentials
- **HeyGen**: Uses API key authentication
- **OpenAI**: Uses API key authentication

### File Handling
- Temporary files are stored in `temp/` directory
- Images are processed through PIL before video creation
- Videos are generated using MoviePy with various effects based on themes

### Error Handling
The codebase includes polling mechanisms for async API operations and comprehensive error handling for API failures and file processing issues.

## Important Files
- `requirements.txt`: Python dependencies
- `docs/heygenAPI.md`: HeyGen API documentation and examples
- `images/`: Test images for video generation
- Downloaded video/image files are saved with task/generation IDs as filenames