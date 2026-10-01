from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request

from app.ai.factory import get_ai_provider
from app.ai.provider import AIProvider
from app.api.dependencies import AppSettings, CurrentUser, DatabaseSession
from app.models import AIAnalysis
from app.schemas.ai_analysis import AIAnalysisRead
from app.services import ai_analysis as service

router = APIRouter(tags=["AI analysis"])
PathID = Annotated[int, Path(gt=0)]


def get_provider_factory(settings: AppSettings) -> Callable[[], AIProvider]:
    # Defer configuration/client resolution until the service has authorized access.
    return lambda: get_ai_provider(settings)


async def require_no_body(request: Request) -> None:
    if await request.body():
        raise HTTPException(422, "This endpoint does not accept a request body")


@router.post("/issues/{issue_id}/ai/analyze", response_model=AIAnalysisRead, status_code=201)
def analyze(issue_id: PathID, user: CurrentUser, db: DatabaseSession,
            provider_factory: Annotated[Callable[[], AIProvider], Depends(get_provider_factory)],
            no_body: Annotated[None, Depends(require_no_body)]) -> AIAnalysis:
    return service.analyze_issue(db, issue_id, user.id, provider_factory)


@router.get("/issues/{issue_id}/ai/analyses", response_model=list[AIAnalysisRead])
def history(issue_id: PathID, user: CurrentUser, db: DatabaseSession) -> list[AIAnalysis]:
    return service.list_analyses(db, issue_id, user.id)
