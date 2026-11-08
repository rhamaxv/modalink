"""Re-ekspor model agar terdaftar ke SQLModel.metadata saat package ini diimpor."""

from app.models.user import Role, User

__all__ = ["Role", "User"]
