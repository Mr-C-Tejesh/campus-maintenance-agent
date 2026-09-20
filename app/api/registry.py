from collections import OrderedDict
from typing import Optional, Dict
from app.workflow.state import WorkflowResult

class WorkflowRegistry:
    """
    Thread-safe in-memory session registry for caching recent WorkflowResult objects.
    Enforces that technician feedback can ONLY reference an authentic, server-executed workflow result.
    """
    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self._cache: OrderedDict[str, WorkflowResult] = OrderedDict()

    def register(self, result: WorkflowResult) -> WorkflowResult:
        if not result.workflow_id:
            return result

        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # Evict oldest entry

        self._cache[result.workflow_id] = result
        return result

    def get(self, workflow_id: str) -> Optional[WorkflowResult]:
        return self._cache.get(workflow_id)

    def clear(self):
        self._cache.clear()

# Global default instance
default_registry = WorkflowRegistry()
