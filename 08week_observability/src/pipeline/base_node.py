import logging
import time
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Generic, TypeVar
from langfuse import get_client

from prometheus_client import Counter, Histogram
from pydantic import BaseModel, ValidationError

from src.prometheus_config import PPROMETHEUS_METRIC_PREFIX, PROMETHEUS_REGISTRY

if TYPE_CHECKING:
    from src.pipeline.context import Context

node_execution_duration = Histogram(
    f"{PPROMETHEUS_METRIC_PREFIX}node_execution_duration_seconds",
    "Time spent executing nodes",
    ["node_name"],
    registry=PROMETHEUS_REGISTRY,
)

node_execution_total = Counter(
    f"{PPROMETHEUS_METRIC_PREFIX}node_execution_total",
    "Total number of node executions",
    ["node_name", "status"],
    registry=PROMETHEUS_REGISTRY,
)

decision_total = Counter(
    f"{PPROMETHEUS_METRIC_PREFIX}decision_total",
    "Total number of decisions made",
    ["node_name", "decision"],
)

logger = logging.getLogger(__name__)


class BaseNode(ABC):
    name: str

    async def execute(self, context: "Context") -> "Context":
        start_time = time.time()
        with get_client().start_as_current_observation(name=self.name, input=context.query) as observation:
            try:
                result = await self._execute(context)
                node_execution_total.labels(node_name=self.name, status="success").inc()
                if result.decision is not None:
                    decision_total.labels(
                        node_name=self.name, decision=str(result.decision)
                    ).inc()
                observation.update(
                    output={
                        "output": result.output,
                        "decision": result.decision or None,
                    }
                )
                return result
            except Exception as e:
                logger.error("Error executing node %s: %s", self.name, str(e))
                node_execution_total.labels(node_name=self.name, status="error").inc()
                observation.update(
                    status_message=str(e),
                )
                raise
            finally:
                duration = time.time() - start_time
                node_execution_duration.labels(node_name=self.name).observe(duration)

    @abstractmethod
    async def _execute(self, context: "Context") -> "Context":
        pass


class BaseDecisionEnum(StrEnum): ...


T = TypeVar("T", bound=BaseDecisionEnum)


class DecisionScheme(BaseModel, Generic[T]):
    reasoning: str
    choice: T


class BaseDecisionNode(BaseNode, Generic[T], ABC):
    available_decisions: type[T]

    @property
    def get_decision_scheme(self) -> type[DecisionScheme[T]]:
        return DecisionScheme[self.available_decisions]

    def parse_decision(self, response: str) -> T:
        try:
            model = self.get_decision_scheme.model_validate_json(response)
            return model.choice
        except ValidationError:
            choice = response.strip()

        try:
            return self.available_decisions(choice)
        except ValueError:
            raise