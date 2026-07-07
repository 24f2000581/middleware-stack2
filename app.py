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

app = FastAPI()

# ==========================
# Rate limit storage
# ==========================
client_requests = defaultdict(list)

# ==========================
# Combined Middleware
# ==========================
@app.middleware("http")
async def middleware(request: Request, call_next):

    # 1. Preflight Bypass: Let browser OPTIONS requests pass without rate limiting
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
        # DOUBLE CORS PROTECTION: Inject explicit CORS headers directly into the early 429 exit
        # to ensure the browser never blocks this response.
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded"
            },
            headers={
                "X-Request-ID": request_id,
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Expose-Headers": "X-Request-ID"
            }
        )

    timestamps.append(now)
    client_requests[client_id] = timestamps

    # 4. Process Request
    response = await call_next(request)

    # 5. Inject Echo Header into Success Paths
    response.headers["X-Request-ID"] = request_id

    return response


# ==========================
# CORS Configuration (CRITICAL: Added LAST to make it the outermost wrapper)
# ==========================
# Using "*" ensures that no matter what dynamic domain or worker sandbox the 
# testing engine uses, the browser will successfully complete the fetch.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"], 
)


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
