from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.provider import AIProvider, InvalidProviderOutput, IssueInput, ProviderError, ProviderNotConfigured, ProviderUnavailable, validate_result
from app.models import AIAnalysis
from app.services.issue import get_issue


class AIAnalysisError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def analyze_issue(db: Session, issue_id: int, actor_id: int, provider_factory: Callable[[], AIProvider]) -> AIAnalysis:
    issue = get_issue(db, issue_id, actor_id)
    issue_input = IssueInput(title=issue.title, description=issue.description)
    # End the request's read transaction and release its connection before network I/O.
    # This service owns the session transaction, like other mutation services.
    db.rollback()
    try:
        provider = provider_factory()
        result = validate_result(provider.analyze_issue(issue_input))
        model_name = provider.model_name
        if not isinstance(model_name, str) or not model_name.strip() or len(model_name) > 200:
            raise InvalidProviderOutput()
    except ProviderNotConfigured:
        raise AIAnalysisError(503, "AI provider is not configured") from None
    except ProviderUnavailable:
        raise AIAnalysisError(503, "AI provider is unavailable") from None
    except ProviderError:
        raise AIAnalysisError(502, "AI provider returned an invalid response") from None

    # Authorization may have changed during the call; recheck before saving history.
    get_issue(db, issue_id, actor_id, lock=True)
    analysis = AIAnalysis(issue_id=issue_id, requested_by_id=actor_id, model_name=model_name,
                          **result.model_dump())
    try:
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    except SQLAlchemyError:
        db.rollback()
        raise AIAnalysisError(503, "Could not save AI analysis") from None
    return analysis


def list_analyses(db: Session, issue_id: int, actor_id: int) -> list[AIAnalysis]:
    get_issue(db, issue_id, actor_id)
    return list(db.scalars(select(AIAnalysis).where(AIAnalysis.issue_id == issue_id)
                           .order_by(AIAnalysis.created_at, AIAnalysis.id)))
