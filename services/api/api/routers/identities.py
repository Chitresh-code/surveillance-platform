from common.ids import new_id
from common.models import Identity, Sighting
from common.pagination import DEFAULT_LIMIT
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.errors import APIError
from api.pagination import paginate
from api.schemas import IdentityListOut, IdentityOut, MergeRequest, SightingListOut, SplitRequest

router = APIRouter(prefix="/identities", tags=["identities"])


def _get_identity_or_404(session: Session, identity_id: str) -> Identity:
    identity = session.get(Identity, identity_id)
    if identity is None:
        raise APIError(404, "identity_not_found", f"No identity with id {identity_id}.")
    return identity


@router.get("", response_model=IdentityListOut)
def list_identities(limit: int = DEFAULT_LIMIT, cursor: str | None = None, session: Session = Depends(get_db)) -> dict:
    rows, next_cursor = paginate(session, select(Identity), Identity, Identity.first_seen, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}


@router.get("/{identity_id}", response_model=IdentityOut)
def get_identity(identity_id: str, session: Session = Depends(get_db)) -> Identity:
    return _get_identity_or_404(session, identity_id)


@router.get("/{identity_id}/sightings", response_model=SightingListOut)
def list_identity_sightings(
    identity_id: str, limit: int = DEFAULT_LIMIT, cursor: str | None = None, session: Session = Depends(get_db)
) -> dict:
    _get_identity_or_404(session, identity_id)
    stmt = select(Sighting).where(Sighting.identity_id == identity_id)
    rows, next_cursor = paginate(session, stmt, Sighting, Sighting.seen_at, limit, cursor)
    return {"data": rows, "next_cursor": next_cursor}


@router.post("/{identity_id}/merge", response_model=IdentityOut)
def merge_identity(identity_id: str, body: MergeRequest, session: Session = Depends(get_db)) -> Identity:
    if body.merge_identity_id == identity_id:
        raise APIError(400, "invalid_merge", "Cannot merge an identity into itself.")
    identity = _get_identity_or_404(session, identity_id)
    other = _get_identity_or_404(session, body.merge_identity_id)

    for sighting in list(other.sightings):
        identity.sightings.append(sighting)
    identity.first_seen = min(identity.first_seen, other.first_seen)
    identity.last_seen = max(identity.last_seen, other.last_seen)
    session.delete(other)
    session.flush()
    return identity


@router.post("/{identity_id}/split", response_model=IdentityOut)
def split_identity(identity_id: str, body: SplitRequest, session: Session = Depends(get_db)) -> Identity:
    identity = _get_identity_or_404(session, identity_id)
    sighting = session.execute(
        select(Sighting).where(Sighting.track_id == body.track_id, Sighting.identity_id == identity_id)
    ).scalar_one_or_none()
    if sighting is None:
        raise APIError(
            404, "sighting_not_found", f"No sighting links track {body.track_id} to identity {identity_id}."
        )

    # ponytail: seeds the split-off identity with the parent's current embedding rather than
    # recomputing from the track's own crops; good enough for an operator correction, revisit
    # if split identities need to re-match on their own appearance.
    new_identity = Identity(
        id=new_id("idn"), first_seen=sighting.seen_at, last_seen=sighting.seen_at, embedding=identity.embedding
    )
    session.add(new_identity)
    session.flush()
    sighting.identity_id = new_identity.id
    return new_identity
