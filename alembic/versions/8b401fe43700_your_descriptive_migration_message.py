"""Your descriptive migration message

Revision ID: 8b401fe43700
Revises: 7bd254d5f198
Create Date: 2025-06-05 14:52:26.501540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b401fe43700'
down_revision: Union[str, None] = '7bd254d5f198'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
