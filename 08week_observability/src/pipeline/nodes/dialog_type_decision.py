from src.clients.llm import get_chat_completion
from src.pipeline.base_node import BaseDecisionEnum, BaseDecisionNode
from src.pipeline.context import Context


class DiloagTypeDecision(BaseDecisionEnum):
    CHIT_CHAT = "CHIT_CHAT"
    RAG = "RAG"
    AGENT = "AGENT"
    HARMFUL = "HARMFUL"


class DialogDecision(BaseDecisionNode[DiloagTypeDecision]):
    available_decisions = DiloagTypeDecision
    name = "dialog_type_decision"

    async def _execute(self, context: Context) -> Context:
        prompt = context.langfuse_client.get_prompt("dialog_type_decision")
        response = await get_chat_completion(
            user_query=context.query,
            prompt=prompt,
            history=context.history,
            settings=context.settings,
            params={
                # standard json request
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "descision",
                        "schema": self.get_decision_scheme.model_json_schema(),
                    },
                },
                "max_completion_tokens": 1024,
                # simplified version of json request. Need to change base method to client.chat.completions.parse
                # "response_format": self.get_decision_scheme,
                # vllm guided choice
                # "extra_body": {
                #     "structured_outputs": {
                #         "choice": [
                #             transition.value for transition in DiloagTypeDecision
                #         ]
                #     }
                # },
            },
        )
        context.decision = self.parse_decision(response)
        return context
