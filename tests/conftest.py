"""Test support: a hermetic fake HTTP transport for the eol.network client.

Avoids any external mocking dependency — mounts a custom requests adapter that
serves canned responses in order and records the PreparedRequests sent, so tests
can assert on URL, method, headers, and body without touching the network.
"""
import json

import pytest
import requests
from requests.adapters import HTTPAdapter
from requests.models import Response


class _Canned:
    def __init__(self, status, json_body, headers):
        self.status = status
        self.json_body = json_body
        self.headers = headers or {}


class FakeTransport(HTTPAdapter):
    def __init__(self):
        super().__init__()
        self.queue = []
        self.requests = []

    def enqueue(self, status=200, json_body=None, headers=None):
        self.queue.append(_Canned(status, json_body, headers))
        return self

    # HTTPAdapter.send(request, stream, timeout, verify, cert, proxies)
    def send(self, request, **kwargs):
        self.requests.append(request)
        canned = self.queue.pop(0) if self.queue else _Canned(200, {}, {})
        resp = Response()
        resp.status_code = canned.status
        payload = canned.json_body if canned.json_body is not None else {}
        resp._content = json.dumps(payload).encode()
        resp.headers["Content-Type"] = "application/json"
        for k, v in canned.headers.items():
            resp.headers[k] = v
        resp.url = request.url
        resp.request = request
        return resp

    @property
    def last_request(self):
        return self.requests[-1]

    def body_json(self, index=-1):
        return json.loads(self.requests[index].body)


@pytest.fixture
def transport():
    return FakeTransport()


@pytest.fixture
def session(transport):
    s = requests.Session()
    s.mount("https://", transport)
    s.mount("http://", transport)
    return s
