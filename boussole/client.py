import json
import urllib.request
from http.client import HTTPResponse
from typing import Any, Dict, Optional


class BoussoleError(Exception):
    """
    BoussoleError that can be raised in case of errors.
    """


class RequestResponse:
    """
    Wrapper around HTTPResponse to provide consistent interface.
    """

    def __init__(self, response: HTTPResponse):
        self.response = response
        self._json_data = None

    @property
    def status_code(self) -> int:
        return self.response.getcode()

    def getcode(self) -> int:
        return self.status_code

    def json(self) -> Any:
        if self._json_data is None:
            self._json_data = json.loads(self.response.read().decode("utf-8"))
        return self._json_data

    @property
    def text(self) -> str:
        return self.response.read().decode("utf-8")

    def read(self) -> bytes:
        return self.response.read()


class GitHubAPI:
    """
    Wrapper for GitHub API calls using urllib.request.
    """

    timeout: int = 10

    def __init__(self, base_url: str, headers: Dict[str, str]):
        self.base_url = base_url
        self.headers = headers

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> RequestResponse:
        url = f"{self.base_url}/{endpoint}"
        request = urllib.request.Request(url, headers=self.headers, method=method)

        if data:
            request.data = json.dumps(data).encode("utf-8")
            request.add_header("Content-Type", "application/json")

        try:
            http_response = urllib.request.urlopen(request, timeout=self.timeout)
            return RequestResponse(http_response)
        except urllib.error.HTTPError as e:
            raise BoussoleError(f"HTTP Error: {e.code} - {e.reason}") from e

    def get(self, endpoint: str) -> RequestResponse:
        return self._make_request("GET", endpoint)

    def post(self, endpoint: str, data: Dict) -> RequestResponse:
        return self._make_request("POST", endpoint, data)

    def put(self, endpoint: str, data: Dict) -> RequestResponse:
        return self._make_request("PUT", endpoint, data)

    def delete(self, endpoint: str, data: Optional[Dict] = None) -> RequestResponse:
        return self._make_request("DELETE", endpoint, data)
