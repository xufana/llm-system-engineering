from prometheus_client import CollectorRegistry

PROMETHEUS_REGISTRY = CollectorRegistry(auto_describe=True)
PPROMETHEUS_METRIC_PREFIX = "bot:"
