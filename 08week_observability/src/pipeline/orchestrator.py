import logging

from src.pipeline.config import Graph
from src.pipeline.context import Context

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, graph: Graph):
        self.graph = graph

    async def execute(self, context: Context) -> str:
        max_steps = len(self.graph.graph) * 2

        node = self.graph.start_node
        while max_steps > 0:
            max_steps -= 1
            logger.info(
                "Executing node=%s",
                node.name,
            )

            try:
                context = await node.node.execute(context)
            except Exception as e:
                logger.exception(e)
                context.output = (
                    "Что-то пошло не так. Попробуйте позже или обратитесь в поддержку."
                )
                raise e

            logger.info(
                "Node %s returned context.decision=%r", node.name, context.decision
            )

            if context.decision is not None:
                next_node_name = node.next_node.get(context.decision)
                if next_node_name is None:
                    context.output = (
                        "Что-то пошло не так. Попробуйте позже или обратитесь в поддержку."
                    )
                    raise ValueError
            else:
                next_node_name = node.next_node

            logger.info(
                "Transitioning from node=%s to next_node=%s",
                node.name,
                next_node_name,
            )

            node = self.graph.name_to_node[next_node_name]
            context.decision = None

            if node.name == self.graph.end_node.name:
                break
        logger.info("Orchestration completed with output=%r", context.output)
        return context.output
