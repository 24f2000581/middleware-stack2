from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import uuid
import time
from collections import defaultdict

EMAIL = "24f2000581@ds.study.iitm.ac.in"

# ==========================
# Assignment values
# ==========================
RATE_LIMIT = 8
WINDOW_SECONDS = 10

# Your assigned CORS origin
ALLOWED_ORIGINS = [
    "https://app-kb6lf9.example.com",
    # Exam page origin
    "https://exam.sanand.workers.dev",
]

app = FastAPI()

# ==========================
# CORS Configuration
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    # Expose custom header so client-side JS can read it
    expose_headers=["X-Request-ID"], 
)

# ==========================
# Rate limit storage
# ==========================
client_requests = defaultdict(list)

# ==========================
# Combined Middleware
# ==========================
@app.middleware("http")
async def middleware(request: Request, call_next):

    # 1. Preflight Bypass: Let browser OPTIONS requests skip rate limiting entirely
    if request.method == "OPTIONS":
        return await call_next(request)

    # 2. Request Context Setup
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    # 3. Rate Limiter Logic
    client_id = request.headers.get("X-Client-Id", "anonymous")
    now = time.time()
    timestamps = client_requests[client_id]

    # Remove timestamps older than 10 seconds
    timestamps = [t for t in timestamps if now - t < WINDOW_SECONDS]

    if len(timestamps) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded"
            },
            headers={"X-Request-ID": request_id}
        )

    timestamps.append(now)
    client_requests[client_id] = timestamps

    # 4. Process Request
    response = await call_next(request)

    # 5. Inject Echo Header into Success Paths
    response.headers["X-Request-ID"] = request_id

    return response

# ==========================
# Routes
# ==========================

@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


@app.get("/")
async def root():
    return {
        "status": "running",
        "endpoint": "/ping"
    }
