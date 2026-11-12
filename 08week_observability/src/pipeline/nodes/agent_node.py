from pydantic_ai import Agent, Tool
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.pipeline.base_node import BaseNode
from src.pipeline.context import Context
from src.tools import calculator, count_words, get_current_time


class AgentNode(BaseNode):
    name = "agent"

    async def _execute(self, context: Context) -> Context:
        model = OpenAIResponsesModel(
            context.settings.llm.name,
            provider=OpenAIProvider(openai_client=context.llm_client),
        )
        agent = Agent(
            model,
            deps_type=str,
            tools=[
                Tool(calculator),
                Tool(get_current_time),
                Tool(count_words),
            ],
            instructions="""""",
        )
        result = await agent.run(context.query)
        context.output = result.output
        return context
