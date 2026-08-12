"""User account queries isolated from HTTP route concerns."""
from core.cruds.base import serialize
from core.cruds.user_crud import UserCRUD

class UserController:
    def __init__(self): self.users = UserCRUD()
    async def get_profile(self, user_id: str):
        return serialize(await self.users.get_by_id(user_id))
