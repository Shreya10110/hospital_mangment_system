# CityCare hospital management system

CityCare is a FastAPI + Supabase PostgreSQL backend with a React/Vite patient portal. It supports secure role-based accounts, hospital and doctor verification, approved doctor-hospital affiliations, appointment booking with patient age and a database-enforced double-booking guard, prescriptions, PDF downloads, a patient-isolated prescription assistant, and safeguarded general health education through Gemini.

## Run locally

1. Create a virtual environment and install the backend dependencies:

   `python -m venv .venv`

   `.venv\Scripts\pip install -r requirements.txt`

2. Copy `.env.example` to `.env`, configure the Supabase PostgreSQL session-pooler `DATABASE_URL`, and set a strong `JWT_SECRET`. Do not commit the resulting `.env` file.

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

- Set `JWT_SECRET` to a unique high-entropy value. The development fallback is intentionally unsuitable for deployment.
- Set backend `CORS_ORIGINS` to the deployed frontend origin and frontend `VITE_API_URL` to the deployed backend URL before building.
- Run the backend with `uvicorn main:app --host 0.0.0.0 --port $PORT` (or your platform's equivalent) without development reload.
- Enable a real admin bootstrap process before deployment; never let a public client promote itself.
- The assistant keeps prescription answers patient-isolated. General questions send only the question—not prescriptions or patient records—to Gemini and are restricted to educational information.
- Prescription PDFs are generated on demand. Cloudinary credentials alone do not upload or persist PDFs.
