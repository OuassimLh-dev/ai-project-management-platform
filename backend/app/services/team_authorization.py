from app.models.team import TeamMember, TeamRole


class TeamError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def require_manager(actor: TeamMember) -> None:
    if actor.role not in (TeamRole.OWNER, TeamRole.ADMIN):
        raise TeamError(403, "Team membership management requires owner or admin")


def require_membership_change(actor: TeamMember, target: TeamMember | None = None,
                              new_role: TeamRole | None = None) -> None:
    require_manager(actor)
    if new_role == TeamRole.OWNER:
        raise TeamError(400, "Ownership transfer is not supported")
    if target is not None and target.role == TeamRole.OWNER:
        raise TeamError(400, "The team owner cannot be removed or demoted")
    if actor.role == TeamRole.ADMIN:
        if (target is not None and target.role != TeamRole.MEMBER) or new_role == TeamRole.ADMIN:
            raise TeamError(403, "Admins may manage ordinary members only")
