"""Beget REST API client with session reuse and structured errors."""

import json
import logging

import requests

from .config import BegetConfig
from .errors import BegetAPIError, BegetAuthError

log = logging.getLogger(__name__)

_client: "BegetClient | None" = None


def init_client(config: BegetConfig) -> "BegetClient":
    global _client
    _client = BegetClient(config)
    return _client


def get_client() -> "BegetClient":
    if _client is None:
        raise RuntimeError("BegetClient not initialised — call init_client() first")
    return _client


class BegetClient:
    """Thin wrapper around Beget shared-hosting REST API.

    All endpoints follow ``POST /api/{section}/{method}`` with:
      - query string: ``output_format=json``
      - form body: ``login``, ``passwd``, and when ``params`` is given
        ``input_format=json`` + ``input_data=<json>``.

    Credentials go in the POST body (not query string) so they don't leak into
    access logs / proxy logs. Log lines here redact ``passwd``.
    """

    API_BASE = "https://api.beget.com/api"

    def __init__(self, config: BegetConfig) -> None:
        self._cfg = config
        self._http = requests.Session()

    def call(self, section: str, method: str, params: dict | None = None) -> dict:
        """Execute an API method and return the parsed answer.

        Raises:
            BegetAuthError: credentials rejected.
            BegetAPIError: any other API-level failure.
            requests.HTTPError: transport-level failure.
        """
        endpoint = f"{self.API_BASE}/{section}/{method}"

        data: dict = {
            "login": self._cfg.login,
            "passwd": self._cfg.password,
        }
        if params is not None:
            data["input_format"] = "json"
            data["input_data"] = json.dumps(params)

        log.debug("%s/%s params=%s", section, method, params)

        resp = self._http.post(
            endpoint,
            params={"output_format": "json"},
            data=data,
            timeout=self._cfg.timeout,
        )
        resp.raise_for_status()

        body: dict = resp.json()

        if body.get("status") == "success":
            return body.get("answer", {})

        err_msg = body.get("error_text", "")
        err_code = body.get("error_code", "")

        # nested errors (some endpoints wrap errors in answer.errors[])
        if not err_msg and "answer" in body:
            answer = body["answer"]
            if isinstance(answer, dict) and "errors" in answer:
                errs = answer["errors"]
                if errs:
                    err_msg = errs[0].get("error_text", "Unknown error")
                    err_code = errs[0].get("error_code", err_code)

        if err_code == "AUTH_ERROR":
            raise BegetAuthError(err_msg or "Bad credentials", code=err_code)

        raise BegetAPIError(
            err_msg or "Unknown error",
            code=err_code,
            details=body,
        )
