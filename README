# HIC Egress Backend

A FastAPI service for managing the secure egress of files from a Trusted Research Environment (TRE). It talks to the UCL Egress backend 
(https://github.com/ucl-arc-tre/egress), handling authentication for HIC.

---

## Tech Stack

- **Python 3.14+** with **FastAPI**
- **Docker** for containerisation
- **Keycloak** for authentication

---

## Prerequisites

- Python 3.14+
- `pip` with a virtualenv

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/hic-egress-backend.git
cd hic-egress-backend
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example env file and fill in the required values:

```
cp .env.example .env
```

Key variables:

| Variable | Description |
|---|---|
| `egress_app_url` | Base URL of the upstream egress/file storage service |
| `fe_url` | Frontend URL (used for CORS allowed origins) |
| `secret_key` | Secret key for signing/encrypting session or internal tokens |
| `egress_username` | Username credential for authenticating with the upstream egress service |
| `egress_password` | Password credential for authenticating with the upstream egress service |
| `KEYCLOAK_SERVER_URL` | Base URL of the Keycloak server (e.g. `https://auth.example.com`) |
| `KEYCLOAK_REALM` | Keycloak realm name |
| `KEYCLOAK_CLIENT_ID` | Client ID registered in Keycloak for this service |
| `KEYCLOAK_CLIENT_SECRET` | Client secret for the Keycloak client |

### 5. Start the development server

```
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`. Or you can build it with docker.

---

## Deployment

### Docker image

```
docker build -t hic-egress-backend .
```
---

## Project Structure

```
app/
├── main.py          # FastAPI app entry point
├── api.py         # Methods for talking to UCL egress app
├── exceptions.py         # Custom exceptions
├── schemas.py         # Pydantic request/response schemas
├── settings.py         # Config file structure and validation
```

---