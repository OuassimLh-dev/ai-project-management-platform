from dataclasses import dataclass
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from app.models.issue import IssuePriority, IssueType


@dataclass(frozen=True)
class IssueInput:
    title: str
    description: str | None


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    summary: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    suggested_type: IssueType
    suggested_priority: IssuePriority
    explanation: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ProviderError(Exception):
    """Known provider failure; never attach upstream bodies or credentials."""


class ProviderUnavailable(ProviderError):
    def __init__(self):
        super().__init__("AI provider is unavailable")


class ProviderNotConfigured(ProviderError):
    def __init__(self):
        super().__init__("AI provider is not configured")


class InvalidProviderOutput(ProviderError):
    def __init__(self):
        super().__init__("AI provider returned invalid output")


def validate_result(value: object) -> AnalysisResult:
    try:
        # Revalidate even constructed model instances at the persistence boundary.
        if isinstance(value, AnalysisResult):
            value = value.model_dump(warnings=False)
        return AnalysisResult.model_validate(value)
    except ValidationError:
        raise InvalidProviderOutput() from None


class AIProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    def analyze_issue(self, issue: IssueInput) -> AnalysisResult: ...
