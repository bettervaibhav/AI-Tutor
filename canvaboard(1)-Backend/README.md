# AI Tutor Backend (Mistral AI + Flask)

## Setup
`
pip install -r requirements.txt
`

## Run
`
python PROJECT_1(AI_TUTOR)/tutor_script_generator.py
`

Server starts at http://localhost:5000

## Endpoints
- GET  /api/health
- POST /api/generate-lesson   body: { "topic": "..." }
- POST /api/resolve-doubt     body: { "doubt": "...", "topic": "..." }

## API Key
Already set in .env file (MISTRAL_API_KEY)
