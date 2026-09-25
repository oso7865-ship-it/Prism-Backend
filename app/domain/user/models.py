from sqlalchemy import BigInteger, CheckConstraint, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.mixins import EntityMixin, UpdatedAtMixin


class User(EntityMixin, UpdatedAtMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("github_user_id", name="uq_users_github_user_id"),
        CheckConstraint("github_user_id > 0", name="ck_users_github_user_id_positive"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_users_status"),
    )

    github_user_id: Mapped[int] = mapped_column(BigInteger)
    login: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), server_default=text("'ACTIVE'"))
