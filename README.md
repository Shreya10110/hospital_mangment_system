# CityCare hospital management system

CityCare is a FastAPI + MongoDB backend with a React/Vite patient portal. It supports secure patient and doctor accounts, hospital discovery, verified doctor listings, appointment booking with a database-enforced double-booking guard, appointment confirmation, prescriptions, and a patient-isolated prescription assistant.

## Run locally

1. Create a virtual environment and install the backend dependencies:

   `python -m venv .venv`

   `.venv\Scripts\pip install -r requirements.txt`

2. Copy `.env.example` to `.env`, configure a MongoDB connection, and set a strong `secret`. Do not commit the resulting `.env` file.

3. Run the API from the project root:

   `uvicorn main:app --reload --port 8010`

   API documentation is available at `http://127.0.0.1:8010/docs`.

4. In another terminal start the frontend:

   `cd frontend`

   `npm install`

   `npm run dev`

   Open `http://localhost:5173`.

   On Windows, `run_local_backend.cmd` and `run_local_frontend.cmd` start both services with the correct local database and API addresses.

## Demo workflow

The first user signup is a patient. Doctor registration is available through `POST /doctors/register`; an administrator verifies a doctor and hospital using the documented admin endpoints, then the doctor applies to the verified hospital. This ensures patients only see verified hospitals and doctor-hospital relationships approved by that hospital.

## Important production notes

- Set `secret` to a unique high-entropy value. The development fallback is intentionally unsuitable for deployment.
- Enable a real admin bootstrap process before deployment; never let a public client promote itself.
- Cloud PDF storage and an external LLM are deliberately configuration points. The included assistant only answers from the authenticated patient's own prescription records and defaults to a safe response when records are missing.
