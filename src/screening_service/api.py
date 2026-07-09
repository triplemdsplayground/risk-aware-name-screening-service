from fastapi import FastAPI

from screening_service.schemas import ScreenRequest, ScreenResponse
from screening_service.service import screen_request

app = FastAPI(title="Risk-aware name screening service")


@app.post("/screen", response_model=ScreenResponse)
def screen(request: ScreenRequest) -> ScreenResponse:
    return screen_request(request)
