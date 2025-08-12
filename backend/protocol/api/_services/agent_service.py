from typing import final

from core.storage.agent_storage import AgentStorage
from protocol.api._api_models import Agent, CreateAgentRequest, Page
from protocol.api._services.conversions import agent_from_domain, create_agent_to_domain


@final
class AgentService:
    def __init__(self, agent_storage: AgentStorage):
        self.agent_storage = agent_storage

    async def list_agents(self) -> Page[Agent]:
        agents = [agent_from_domain(agent) for agent in await self.agent_storage.list_agents()]
        return Page(items=agents, total=len(agents))

    async def create_agent(self, agent: CreateAgentRequest) -> Agent:
        domain_agent = create_agent_to_domain(agent)
        await self.agent_storage.store_agent(domain_agent)
        return agent_from_domain(domain_agent)
