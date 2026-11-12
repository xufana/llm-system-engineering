from src.clients.qdrant import get_documents
from src.pipeline.base_node import BaseNode
from src.pipeline.context import Context


class RetrieveNode(BaseNode):
    name = "retrieve"

    async def _execute(self, context: Context) -> Context:
        documents = await get_documents(
            query=context.query,
            settings=context.settings,
            top_k=5,
        )
        context.documents = documents
        return context
