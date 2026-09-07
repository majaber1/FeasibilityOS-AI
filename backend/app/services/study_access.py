"""
Shared study-ownership checks.

A study's owner is always derived from its parent project's owner_id -- a
study has no owner_id of its own. Every router that reads or mutates a study
(or anything scoped under a study: evidence, assumptions, ...) must go through
owned_study_or_error so ownership is enforced identically everywhere and is
never trusted from client input.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from app.api.auth import UserOut


def can_access_owner(user: UserOut, owner_id: Optional[int]) -> bool:
    """Admins access anything; everyone else only their own resources."""
    return user.role_key == "admin" or (owner_id is not None and owner_id == user.id)


def project_owner_id(db, models, project_id) -> Optional[int]:
    project = db.get(models.Project, project_id) if project_id is not None else None
    return project.owner_id if project is not None else None


def owned_study_or_error(db, models, study_id: int, user: UserOut):
    """Fetch a study enforcing ownership via its project owner.

    404 when the study does not exist; 403 when it exists but the caller is
    not the owner (and not an admin). Never leaks another user's study
    contents through the error response.
    """
    study = db.get(models.FeasibilityStudy, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail="Study not found")
    owner_id = project_owner_id(db, models, study.project_id)
    if not can_access_owner(user, owner_id):
        raise HTTPException(status_code=403, detail="Not authorized for this study")
    return study
