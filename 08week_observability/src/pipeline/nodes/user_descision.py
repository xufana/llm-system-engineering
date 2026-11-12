from schemes import RolesEnum
from src.pipeline.base_node import BaseDecisionEnum, BaseDecisionNode
from src.pipeline.context import Context


class UserTypeDecision(BaseDecisionEnum):
    USER = "user"
    ADMIN = "admin"


class UserDecision(BaseDecisionNode[UserTypeDecision]):
    available_decisions = UserTypeDecision
    name = "user_type_decision"

    async def _execute(self, context: Context) -> Context:
        if context.role == RolesEnum.USER:
            context.decision = UserTypeDecision.USER
        else:
            context.decision = UserTypeDecision.ADMIN
        return context
