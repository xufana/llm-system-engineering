from src.pipeline.base_node import BaseNode
from src.pipeline.context import Context


class FinalNode(BaseNode):
    name = "final_node"

    async def _execute(self, context: Context) -> Context:
        return context
