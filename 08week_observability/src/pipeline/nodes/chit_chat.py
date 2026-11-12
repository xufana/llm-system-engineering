from src.clients.llm import get_chat_completion
from src.pipeline.base_node import BaseNode
from src.pipeline.context import Context


class ChitChatNode(BaseNode):
    name = "chit_chat"

    async def _execute(self, context: Context) -> Context:
        prompt = context.langfuse_client.get_prompt("chit-chat")
        response = await get_chat_completion(
            user_query=context.query,
            history=context.history,
            settings=context.settings,
            prompt=prompt,
        )
        context.output = response
        return context


class ChitChatAdminNode(BaseNode):
    name = "chit_chat_admin"

    async def _execute(self, context: Context) -> Context:
        prompt = """Ответь что сегодня солнечно"""
        response = await get_chat_completion(
            user_query=context.query,
            system_message=prompt,
            history=context.history,
            settings=context.settings,
        )
        context.output = response
        return context
