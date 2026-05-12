"""Unit tests: medical clearance validity (1 year rule).

Designed by: <Student name / ID — fill in for the course report>.
"""

from datetime import date

from gym_management.domain.membership.medical_report import MedicalReport


def test_medical_report_not_expired_day_before_expiry() -> None:
    issued = date(2025, 5, 12)
    report = MedicalReport(id=1, institution_name="Örnek Aile Sağlığı", issued_on=issued)
    assert report.expires_on() == date(2026, 5, 12)
    assert report.is_expired(as_of=date(2026, 5, 12)) is False
    assert report.days_until_expiry(as_of=date(2026, 5, 11)) == 1


def test_medical_report_expires_day_after_expiry_boundary() -> None:
    issued = date(2025, 5, 12)
    report = MedicalReport(id=2, institution_name="Örnek Aile Sağlığı", issued_on=issued)
    assert report.is_expired(as_of=date(2026, 5, 13)) is True
    assert report.days_until_expiry(as_of=date(2026, 5, 13)) == -1


def test_medical_report_leap_year_issue_date_clamps() -> None:
    """Feb 29 issuance: expiry should land on Feb 28 the following year (calendar clamp)."""
    issued = date(2024, 2, 29)
    report = MedicalReport(id=3, institution_name="Örnek Hastane", issued_on=issued)
    assert report.expires_on() == date(2025, 2, 28)
