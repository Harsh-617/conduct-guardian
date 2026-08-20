"""account contact info

Adds `contact_email` and `contact_phone` to `accounts`, both nullable with a
unique index. These carry the sender's real channel identity (an email
address or phone number) so an inbound message can be resolved to its account
by who actually sent it, instead of a manually-typed account tag —
`app.accounts.resolve_account_by_contact` is the lookup that reads them.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-21

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts", sa.Column("contact_email", sa.String(length=255), nullable=True)
    )
    op.create_index(
        "ix_accounts_contact_email", "accounts", ["contact_email"], unique=True
    )

    op.add_column(
        "accounts", sa.Column("contact_phone", sa.String(length=32), nullable=True)
    )
    op.create_index(
        "ix_accounts_contact_phone", "accounts", ["contact_phone"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_accounts_contact_phone", table_name="accounts")
    op.drop_column("accounts", "contact_phone")

    op.drop_index("ix_accounts_contact_email", table_name="accounts")
    op.drop_column("accounts", "contact_email")
