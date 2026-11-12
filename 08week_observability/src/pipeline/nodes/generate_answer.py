from src.clients.llm import get_chat_completion
from src.pipeline.base_node import BaseNode
from src.pipeline.context import Context


class LLMAnswer(BaseNode):
    name = "llm_answer"

    async def _execute(self, context: Context) -> Context:
        formatted_documents = []
        for i, document in enumerate(context.documents):
            formatted_documents.append(f"Документ {i} " + document)

        response = await get_chat_completion(
            user_query=context.query
            + "\n\nДокументы:\n"
            + "\n\n".join(formatted_documents),
            history=context.history,
            settings=context.settings,
            system_message="You're assistant"
        )
        context.output = response
        return context
