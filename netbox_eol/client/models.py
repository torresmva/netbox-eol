"""Typed result objects for the eol.network client.

Plain dataclasses — no Django. Dates are kept as ISO strings at this boundary;
the model layer coerces them. `raw` retains the full upstream payload.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KevInfo:
    exposed: bool
    count: int
    cve_ids: list
    catalog_version: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, d):
        if d is None:
            return None
        return cls(
            exposed=bool(d.get("exposed", False)),
            count=int(d.get("count", 0)),
            cve_ids=list(d.get("cve_ids", []) or []),
            catalog_version=d.get("catalog_version"),
            updated_at=d.get("updated_at"),
        )


@dataclass
class ProductRecord:
    vendor_slug: str
    product_id: str
    product_name: Optional[str] = None
    product_type: Optional[str] = None
    applicable_series: list = field(default_factory=list)
    series_slug: Optional[str] = None
    category: Optional[str] = None
    lifecycle_status: Optional[str] = None
    announcement_date: Optional[str] = None
    end_of_sale_date: Optional[str] = None
    last_date_of_support: Optional[str] = None
    end_of_sw_maintenance_date: Optional[str] = None
    end_of_vuln_security_support_date: Optional[str] = None
    end_of_routine_failure_analysis_date: Optional[str] = None
    replacement_product: Optional[str] = None
    url: Optional[str] = None
    kev: Optional[KevInfo] = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d):
        if d is None:
            return None
        return cls(
            vendor_slug=d.get("vendor_slug") or d.get("vendor"),
            product_id=d.get("product_id"),
            product_name=d.get("product_name"),
            product_type=d.get("product_type"),
            applicable_series=list(d.get("applicable_series", []) or []),
            series_slug=d.get("series_slug"),
            category=d.get("category"),
            lifecycle_status=d.get("lifecycle_status"),
            announcement_date=d.get("announcement_date"),
            end_of_sale_date=d.get("end_of_sale_date"),
            last_date_of_support=d.get("last_date_of_support"),
            end_of_sw_maintenance_date=d.get("end_of_sw_maintenance_date"),
            end_of_vuln_security_support_date=d.get("end_of_vuln_security_support_date"),
            end_of_routine_failure_analysis_date=d.get("end_of_routine_failure_analysis_date"),
            replacement_product=d.get("replacement_product"),
            url=d.get("url"),
            kev=KevInfo.from_dict(d.get("kev")),
            raw=d,
        )


@dataclass
class MatchRow:
    ref: Optional[str]
    query: Optional[str]
    vendor: Optional[str]
    vendor_resolved: Optional[str]
    matched: bool
    confidence: str
    match: Optional[ProductRecord] = None
    error: Optional[dict] = None

    @classmethod
    def from_dict(cls, d):
        return cls(
            ref=d.get("ref"),
            query=d.get("query"),
            vendor=d.get("vendor"),
            vendor_resolved=d.get("vendor_resolved"),
            matched=bool(d.get("matched", False)),
            confidence=d.get("confidence", "none"),
            match=ProductRecord.from_dict(d.get("match")),
            error=d.get("error"),
        )


@dataclass
class KevLookupResult:
    vendor_slug: str
    product_id: str
    found: bool
    kev: Optional[KevInfo] = None

    @classmethod
    def from_dict(cls, d):
        return cls(
            vendor_slug=d.get("vendor_slug"),
            product_id=d.get("product_id"),
            found=bool(d.get("found", False)),
            kev=KevInfo.from_dict(d.get("kev")),
        )
