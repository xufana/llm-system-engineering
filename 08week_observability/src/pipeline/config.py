import dataclasses

from src.pipeline.base_node import BaseDecisionEnum, BaseDecisionNode, BaseNode
from src.pipeline.nodes.agent_node import AgentNode
from src.pipeline.nodes.chit_chat import ChitChatAdminNode, ChitChatNode
from src.pipeline.nodes.dialog_type_decision import DialogDecision, DiloagTypeDecision
from src.pipeline.nodes.final import FinalNode
from src.pipeline.nodes.generate_answer import LLMAnswer
from src.pipeline.nodes.get_context import RetrieveNode
from src.pipeline.nodes.harmful import HarmfulNode
from src.pipeline.nodes.user_descision import UserDecision, UserTypeDecision


@dataclasses.dataclass
class Node:
    name: str
    node: BaseNode | BaseDecisionNode
    next_node: str | dict[BaseDecisionEnum, str] | None


class Graph:
    def __init__(self, nodes: list[Node], start_node_name: str, end_node_name: str):
        self.graph = nodes
        self.name_to_node: dict[str, Node] = {node.name: node for node in nodes}
        if (
            start_node_name not in self.name_to_node
            or end_node_name not in self.name_to_node
        ):
            raise ValueError(
                f"Node {start_node_name} or {end_node_name} does not exist"
            )

        self.start_node = self.name_to_node[start_node_name]
        self.end_node = self.name_to_node[end_node_name]
        self.validate_transitions()
        self.validate_paths()

    def validate_transitions(self) -> bool:
        """
        Validate that all node transitions reference existing nodes.
        Raises ValueError if validation fails.
        """
        for node in self.graph:
            if node.next_node is None:
                continue
            elif isinstance(node.next_node, str):
                if node.next_node not in self.name_to_node:
                    raise ValueError(
                        f"Node '{node.name}' references non-existent node '{node.next_node}'"
                    )
            elif isinstance(node.next_node, dict):
                for decision, next_node_name in node.next_node.items():
                    if next_node_name not in self.name_to_node:
                        raise ValueError(
                            f"Node '{node.name}' references non-existent node '{next_node_name}' "
                            f"for decision '{decision.value}'"
                        )
        return True

    def validate_paths(self) -> bool:
        """
        Validate that all paths from start node eventually reach the end node.
        Raises ValueError if validation fails.
        """
        visited = set()

        def dfs_backwards(node_name: str) -> bool:
            """Perform DFS from end node backwards to find all reachable nodes."""
            if node_name in visited:
                return True
            visited.add(node_name)

            # Find all nodes that point to this node
            for node in self.graph:
                if node.next_node is None:
                    continue
                elif isinstance(node.next_node, str):
                    if node.next_node == node_name and node.name not in visited:
                        dfs_backwards(node.name)
                elif isinstance(node.next_node, dict):
                    if (
                        node_name in node.next_node.values()
                        and node.name not in visited
                    ):
                        dfs_backwards(node.name)

            return True

        dfs_backwards(self.end_node.name)

        if self.start_node.name not in visited:
            raise ValueError(
                f"Start node '{self.start_node.name}' does not lead to end node '{self.end_node.name}'"
            )

        # Check if all nodes are on a path from start to end
        all_node_names = {node.name for node in self.graph}
        unreachable = all_node_names - visited
        if unreachable:
            raise ValueError(
                f"Nodes {unreachable} are not on any path from start to end node"
            )

        return True

    def to_mermaid(self) -> str:
        """Generate a Mermaid flowchart diagram representation of the graph."""
        lines = ["graph TD"]

        first_node = self.graph[0].name if self.graph else None
        last_nodes = set()

        for node in self.graph:
            if node.next_node is None:
                last_nodes.add(node.name)

        for node in self.graph:
            # Determine node shape based on type
            if isinstance(node.node, BaseDecisionNode):
                lines.append(f'    {node.name}{{"{node.name}"}}')
            else:
                lines.append(f'    {node.name}["{node.name}"]')

            # Add edges
            if node.next_node is None:
                continue
            elif isinstance(node.next_node, str):
                lines.append(f"    {node.name} --> {node.next_node}")
            elif isinstance(node.next_node, dict):
                for decision, next_node_name in node.next_node.items():
                    lines.append(
                        f"    {node.name} -->|{decision.value}| {next_node_name}"
                    )

        # Add styles
        if first_node:
            lines.append("    classDef startNode fill:#90EE90")
            lines.append(f"    class {first_node} startNode")

        if last_nodes:
            lines.append("    classDef endNode fill:#FFB6C6")
            lines.append(f"    class {','.join(last_nodes)} endNode")

        return "\n".join(lines)


CHAT_BOT = Graph(
    [
        Node(
            name="chat_type",
            node=DialogDecision(),
            next_node={
                DiloagTypeDecision.RAG: "retrieval",
                DiloagTypeDecision.CHIT_CHAT: "user_type_descision",
                DiloagTypeDecision.AGENT: "agent",
                DiloagTypeDecision.HARMFUL: "harmful",
            },
        ),
        Node(
            name="user_type_descision",
            node=UserDecision(),
            next_node={
                UserTypeDecision.USER: "chit_chat",
                UserTypeDecision.ADMIN: "admin_chit_chat",
            },
        ),
        Node(
            name="chit_chat",
            node=ChitChatNode(),
            next_node="final",
        ),
        Node(
            name="admin_chit_chat",
            node=ChitChatAdminNode(),
            next_node="final",
        ),
        Node(
            name="agent",
            node=AgentNode(),
            next_node="final",
        ),
        Node(
            name="harmful",
            node=HarmfulNode(),
            next_node="final",
        ),
        Node(
            name="retrieval",
            node=RetrieveNode(),
            next_node="answer",
        ),
        Node(
            name="answer",
            node=LLMAnswer(),
            next_node="final",
        ),
        Node(
            name="final",
            node=FinalNode(),
            next_node=None,
        ),
    ],
    start_node_name="chat_type",
    end_node_name="final",
)

if __name__ == "__main__":
    print(CHAT_BOT.to_mermaid())
