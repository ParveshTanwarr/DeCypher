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
@app.get("/server-status")
def server_status():
    return {
        "service": "DeCypher Mock Service",
        "page_type": "authorized-test-status-page",
        "server_status": "operational",
        "test_indicator": "EXPOSED_STATUS_PAGE_TEST"
    }
@app.get("/descriptor-timing")
def descriptor_timing():
    return {
        "marker": "DESCRIPTOR_TIMING_TEST",
        "timing": "authorized-test-signal"
    }