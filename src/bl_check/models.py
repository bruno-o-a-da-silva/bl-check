"""The three documents of one export booking. Pydantic validates JSON from files or HTTP."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Booking(BaseModel):
    ref: str
    consignee: str
    quantity: int = Field(ge=1, description="Containers booked")
    size_type: str = Field(description="ISO size-type code, e.g. 22G1 or 45G1")
    packages: int = Field(ge=0)
    hs_headings: list[str] = Field(description="Four-digit HS headings declared at booking")
    si_cutoff: datetime = Field(description="Cut-off for shipping instructions (B/L draft)")
    vgm_cutoff: datetime


class Vgm(BaseModel):
    """SOLAS VI/2 method 2: gross mass = cargo + packing + tare, all in kg."""

    container: str
    cargo_kg: int = Field(ge=0)
    packing_kg: int = Field(ge=0)
    tare_kg: int = Field(ge=0)
    declared_kg: int = Field(ge=0)


class DraftContainer(BaseModel):
    number: str
    packages: int = Field(ge=0)
    gross_kg: int = Field(ge=0, description="Cargo plus packing, without tare")


class HsLine(BaseModel):
    code: str
    packages: int = Field(ge=0)
    gross_kg: int = Field(ge=0)


class Draft(BaseModel):
    consignee: str
    containers: list[DraftContainer]
    hs_lines: list[HsLine]


class Shipment(BaseModel):
    booking: Booking
    vgm: list[Vgm]
    draft: Draft
