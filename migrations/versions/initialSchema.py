"""Initial Helmet Workbench schema."""

from __future__ import annotations

from alembic import op

from helmet_workbench.db.models import Base

revision = "20261107_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
