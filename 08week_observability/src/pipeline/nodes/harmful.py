from src.clients.llm import get_chat_completion
from src.pipeline.base_node import BaseNode
from src.pipeline.context import Context


class HarmfulNode(BaseNode):
    name = "harmful"

    async def _execute(self, context: Context) -> Context:
        prompt = """Ты отвечаешь на грубые сообщения. Проси пользователя чтобы он был более вежлив"""
        response = await get_chat_completion(
            user_query=context.query,
            system_message=prompt,
            history=context.history,
            settings=context.settings,
        )
        context.output = response
        return context
