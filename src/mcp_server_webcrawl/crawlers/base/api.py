import json

from datetime import datetime
from time import time
from typing import Any

from mcp_server_webcrawl.models import METADATA_VALUE_TYPE, UTC
from mcp_server_webcrawl.models.resources import ResourceResultType, ResourceResult
from mcp_server_webcrawl.models.sites import SiteResult
from mcp_server_webcrawl.utils.logger import get_logger

logger = get_logger()

OVERRIDE_ERROR_MESSAGE: str = "BaseCrawler subclasses must implement \
the following methods: handle_list_tools, handle_call_tool"

class BaseJsonApiEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for BaseJsonApi objects and ResourceResultType enums.
    """

    def default(self, obj) -> Any:
        """
        Override default encoder to handle custom types.

        Args:
            obj: Object to encode

        Returns:
            JSON serializable representation of the object
        """
        if isinstance(obj, BaseJsonApi):
            return obj.__dict__
        elif isinstance(obj, ResourceResultType):
            return obj.value
        return super().default(obj)

class BaseJsonApi:
    """
    Base class for JSON API responses.

    Provides a standardized structure for API responses including metadata,
    results, and error handling.
    """

    def __init__(self, method: str, args: dict[str, Any]):
        """
        Construct with the arguments of creation (aoc), these will be echoed back in
        JSON response. This is an object that collapses into json on json dumps. This is
        done with everything within implementing to_dict.

        Args:
            method: API method name
            args: Dictionary of API arguments
        """

        from mcp_server_webcrawl import __version__, __name__
        self._start_time = time()
        self.method = method
        self.args = args
        self.meta_generator = f"{__name__} ({__version__})"
        self.meta_generated = datetime.now(UTC).isoformat()
        self._results: list[SiteResult | ResourceResult] = []
        self._results_total: int = 0
        self._results_offset: int = 0
        self._results_limit: int = 0
        self._errors: list[str] = []

    @property
    def total(self) -> int:
        """
        Returns the total number of results.

        Returns:
            Integer count of total results
        """
        return self._results_total

    def get_results(self) -> list[SiteResult | ResourceResult]:
        return self._results.copy()

    def set_results(self, results: list[SiteResult | ResourceResult], total: int, offset: int, limit: int) -> None:
        """
        Set the results of the API response.

        Args:
            results: List of result objects
            total: Total number of results (including those beyond limit)
            offset: Starting position in the full result set
            limit: Maximum number of results to include
        """

        self._results = results
        self._results_total = total
        self._results_offset = offset
        self._results_limit = limit

    def append_error(self, message: str) -> None:
        """
        Add an error to the JSON response, visible to the endpoint LLM.

        Args:
            message: Error message to add
        """
        self._errors.append(message)

    def to_dict(self) -> dict[str, METADATA_VALUE_TYPE]:
        """
        Convert the object to a JSON-serializable dictionary.

        Returns:
            Dictionary representation of the API response
        """

        response: dict[str, Any] = {
            "__meta__": {
                "generator": f"{self.meta_generator}",
                "generated": f"{self.meta_generated}",
                "request": {
                    "method": f"{self.method}",
                    "arguments": self.args,
                    "time": time() - self._start_time,
                },
                "results": {
                    "total": self._results_total,
                    "offset": self._results_offset,
                    "limit": self._results_limit,
                },
            },
            "results": [r.to_forcefield_dict(self.args["fields"]) if hasattr(r, "to_forcefield_dict") else r for r in self._results]
        }

        if self._errors:
            response["__meta__"]["errors"] = self._errors

        return response

    def to_json(self) -> str:
        """
        Return a JSON serializable representation of this object.

        Returns:
            JSON string representation of the API response
        """
        return json.dumps(self.to_dict(), cls=BaseJsonApiEncoder)
