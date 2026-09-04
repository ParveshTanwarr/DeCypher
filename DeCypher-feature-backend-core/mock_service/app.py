from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI(title="DeCypher Mock Service")


@app.get("/")
def home():
    return PlainTextResponse(
        "DeCypher Mock Hidden Service - Authorized Test Environment",
        headers={
            "X-DeCypher-Test-Banner": "MOCK-SERVER-V1"
        }
    )


@app.get("/status")
def status():
    return {
        "status": "operational",
        "environment": "authorized-test"
    }