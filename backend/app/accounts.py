"""Account resolution by real contact identity, shared across channels.

`resolve_account_by_contact` is the email/SMS counterpart to `/screen`'s
account resolution: instead of trusting a caller-supplied `external_id` (a
manually-typed tag — fine when a human is filling in a Live Screening form),
it identifies the account from the sender's actual contact info, so the same
sender always lands on the same account across messages.
"""

from __future__ import annotations

import secrets

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account


def _generate_external_id() -> str:
    """A short, effectively-unique reference for a contact-created account.

    Distinct from the seeded 4-digit numeric ids so the two origins are easy
    to tell apart at a glance in the UI.
    """
    return f"C-{secrets.token_hex(4).upper()}"


async def resolve_account_by_contact(
    session: AsyncSession, *, email: str | None = None, phone: str | None = None
) -> Account:
    """Find the account matching `email` or `phone`, creating one if none exists.

    Same auto-create philosophy as `/screen`'s account resolution — an
    unrecognised sender still gets screened, not rejected — except identity
    here comes from the contact info actually used to send the message, not
    from a field the sender could type anything into.
    """
    if not email and not phone:
        raise ValueError("resolve_account_by_contact requires an email or phone")

    conditions = []
    if email:
        conditions.append(Account.contact_email == email)
    if phone:
        conditions.append(Account.contact_phone == phone)

    found = await session.execute(select(Account).where(or_(*conditions)))
    account = found.scalars().first()
    if account is not None:
        return account

    account = Account(
        external_id=_generate_external_id(),
        contact_email=email,
        contact_phone=phone,
    )
    session.add(account)
    await session.flush()
    return account
