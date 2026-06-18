"""Framework-free HTTP client for the eol.network /integrations/* API.

No Django imports — unit-testable in isolation.
"""

import time

import requests

from netbox_eol.client.exceptions import EolApiError, EolAuthError, EolRateLimited
from netbox_eol.client.models import KevLookupResult, MatchRow

CHUNK_SIZE = 100


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


class EolClient:
    def __init__(
        self,
        base_url,
        api_key,
        user_agent,
        *,
        timeout=10,
        max_retries=3,
        session=None,
        sleep=time.sleep,
    ):
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.api_key = api_key
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep = sleep
        self.session = session or requests.Session()

    def _headers(self):
        return {
            "User-Agent": self.user_agent,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _error_code(resp):
        try:
            return (resp.json() or {}).get("error", {}).get("code")
        except ValueError:
            return None

    def _request(self, method, path, json=None):
        url = self.base_url + path
        attempt = 0
        while True:
            resp = self.session.request(
                method, url, json=json, headers=self._headers(), timeout=self.timeout
            )
            status = resp.status_code
            if status < 400:
                return resp.json()

            code = self._error_code(resp)
            if status in (401, 403):
                raise EolAuthError(f"{status} {code}", code=code, status=status)
            if status == 429:
                if attempt >= self.max_retries:
                    raise EolRateLimited(f"429 {code}", code=code, status=status)
                self.sleep(self._retry_after(resp, attempt))
                attempt += 1
                continue
            if status >= 500:
                if attempt >= self.max_retries:
                    raise EolApiError(f"{status} {code}", code=code, status=status)
                self.sleep(2**attempt)
                attempt += 1
                continue
            # other 4xx (400 bad_request / bad_user_agent) — not retryable
            raise EolApiError(f"{status} {code}", code=code, status=status)

    @staticmethod
    def _retry_after(resp, attempt):
        header = resp.headers.get("Retry-After")
        if header is not None:
            try:
                return int(header)
            except ValueError:
                pass
        return 2**attempt

    @staticmethod
    def _check_envelope(body, endpoint):
        data = body.get("data", [])
        meta = body.get("meta", {})
        if "requested" in meta and len(data) != meta["requested"]:
            raise EolApiError(
                f"{endpoint} returned {len(data)} rows for {meta['requested']} requested "
                "(contract guarantees len(data) == meta.requested)"
            )
        return data

    def match(self, queries):
        valid, invalid_rows = [], []
        for q in queries:
            if len((q.get("q") or "").strip()) < 2:
                invalid_rows.append(
                    MatchRow(
                        ref=q.get("ref"),
                        query=q.get("q"),
                        vendor=q.get("vendor"),
                        vendor_resolved=None,
                        matched=False,
                        confidence="none",
                        error={"code": "q_too_short", "message": "q must be at least 2 characters"},
                    )
                )
            else:
                valid.append(q)

        rows = []
        for chunk in _chunks(valid, CHUNK_SIZE):
            body = self._request("POST", "integrations/match", json={"queries": chunk})
            data = self._check_envelope(body, "match")
            rows.extend(MatchRow.from_dict(r) for r in data)
        return rows + invalid_rows

    def kev_lookup(self, products):
        results = []
        for chunk in _chunks(list(products), CHUNK_SIZE):
            body = self._request("POST", "integrations/kev/lookup", json={"products": chunk})
            data = self._check_envelope(body, "kev_lookup")
            results.extend(KevLookupResult.from_dict(r) for r in data)
        return results

    def search(self, q, vendor=None):
        params = {"q": q}
        if vendor:
            params["vendor"] = vendor
        resp = self.session.get(
            self.base_url + "search",
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        return (resp.json() or {}).get("data", [])
