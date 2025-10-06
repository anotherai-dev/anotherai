from typing import NamedTuple, Protocol


class UserDetails(NamedTuple):
    id: str
    email: str
    name: str


class OrganizationDetails(NamedTuple):
    id: str
    name: str
    slug: str


class UserService(Protocol):
    async def get_organization(self, org_id: str) -> OrganizationDetails: ...
    async def get_org_admins(self, org_id: str) -> list[UserDetails]: ...
    async def get_user(self, user_id: str) -> UserDetails: ...
