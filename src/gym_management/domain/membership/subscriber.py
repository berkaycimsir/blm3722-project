"""Gym subscriber aggregate root (links to medical clearance)."""

from dataclasses import dataclass


@dataclass(slots=True)
class Subscriber:
    """Persists subscriber profile; medical_report_id joins MedicalReport."""

    id: int | None
    full_name: str
    email: str
    phone: str
    medical_report_id: int | None
