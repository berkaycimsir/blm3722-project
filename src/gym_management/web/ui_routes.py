"""HTML pages backed by the same repositories as the JSON API."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from gym_management.api.deps import get_db
from gym_management.domain.equipment.equipment import Equipment, EquipmentStatus
from gym_management.domain.equipment.maintenance_record import MaintenanceRecord
from gym_management.domain.equipment.repair_record import RepairRecord
from gym_management.domain.finance.budget import BudgetCategory, BudgetLine
from gym_management.domain.finance.payment import Payment
from gym_management.domain.membership.medical_report import MedicalReport
from gym_management.domain.membership.subscriber import Subscriber
from gym_management.domain.subscription.package_factory import create_subscription_package
from gym_management.domain.subscription.schedule_strategy import PackageKind
from gym_management.domain.subscription.billing import subscription_expected_total
from gym_management.domain.subscription.subscription import Subscription, SubscriptionStatus
from gym_management.domain.subscription.subscription_package import SubscriptionPackage
from gym_management.infrastructure.repo_sqlalchemy import (
    SqlBudgetLineRepository,
    SqlEquipmentRepository,
    SqlMedicalReportRepository,
    SqlMaintenanceRepository,
    SqlPaymentRepository,
    SqlRepairRepository,
    SqlSubscriberRepository,
    SqlSubscriptionPackageRepository,
    SqlSubscriptionRepository,
)

WEB_DIR = Path(__file__).resolve().parent
_JINJA = Environment(
    loader=FileSystemLoader(str(WEB_DIR / "templates")),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_page(request: Request, template_name: str, **context: Any) -> HTMLResponse:
    """Render HTML without Starlette's Jinja2Templates (fixes Starlette 1.x + Jinja cache bug)."""
    tpl = _JINJA.get_template(template_name)
    html = tpl.render(request=request, **context)
    return HTMLResponse(html)


router = APIRouter(tags=["web-ui"])


def _redirect(path: str, **query: str) -> RedirectResponse:
    if query:
        q = "&".join(f"{k}={quote(v, safe='')}" for k, v in query.items() if v)
        path = f"{path}?{q}"
    return RedirectResponse(path, status_code=303)


def _parse_amount(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return str(Decimal(raw))
    except InvalidOperation:
        return None


def _billing_cycle_label(months: int) -> str:
    m = max(1, int(months))
    if m == 1:
        return "aylık"
    if m == 12:
        return "yıllık"
    return f"{m} aylık"


def _parse_time_hm(raw: str) -> time | None:
    raw = raw.strip()
    if not raw:
        return None
    parts = raw.split(":")
    try:
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return time(h, m)


def _month_bounds(y: int, m: int) -> tuple[date, date]:
    start = date(y, m, 1)
    end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return start, end


def _payments_trend_series(db: Session, today: date, months: int = 6) -> dict[str, list]:
    pay = SqlPaymentRepository(db)
    labels: list[str] = []
    values: list[float] = []
    y, m = today.year, today.month
    seq: list[tuple[int, int]] = []
    for _ in range(months):
        seq.append((y, m))
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    seq.reverse()
    for y, m in seq:
        start_d, end_d = _month_bounds(y, m)
        start_dt = datetime.combine(start_d, datetime.min.time())
        end_dt = datetime.combine(end_d, datetime.min.time())
        labels.append(f"{m:02d}/{str(y)[2:]}")
        values.append(float(Decimal(pay.total_between(start_dt, end_dt))))
    return {"labels": labels, "values": values}


def _budget_chart_rows(lines: list[BudgetLine]) -> dict[str, list]:
    names = {
        BudgetCategory.SUBSCRIPTION_REVENUE: "Abonelik geliri",
        BudgetCategory.MAINTENANCE_EXPENSE: "Bakım gideri",
        BudgetCategory.REPAIR_EXPENSE: "Tamir gideri",
    }
    labels: list[str] = []
    planned: list[float] = []
    actual: list[float] = []
    for ln in lines:
        if ln.id is None:
            continue
        labels.append(names.get(ln.category, ln.category.value))
        planned.append(float(Decimal(ln.planned_amount)))
        actual.append(float(Decimal(ln.actual_amount)))
    return {"labels": labels, "planned": planned, "actual": actual}


@router.get("/", response_class=HTMLResponse)
def root_redirect() -> RedirectResponse:
    return RedirectResponse("/ui/", status_code=302)


@router.get("/ui/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    subs = SqlSubscriberRepository(db).list()
    pkgs = SqlSubscriptionPackageRepository(db).list()
    equip = SqlEquipmentRepository(db).list()
    today = date.today()
    horizon_end = today + timedelta(days=30)
    raw_expiring = SqlMedicalReportRepository(db).list_expiring_before(horizon_end)
    expiring_reports = [
        r
        for r in raw_expiring
        if r.id is not None and today <= r.expires_on() <= horizon_end
    ]
    start_m, end_m = _month_bounds(today.year, today.month)
    mtd_a = datetime.combine(start_m, datetime.min.time())
    mtd_b = datetime.combine(end_m, datetime.min.time())
    payments_mtd = SqlPaymentRepository(db).total_between(mtd_a, mtd_b)
    budget_lines = SqlBudgetLineRepository(db).list_period(today.year, today.month)
    trend = _payments_trend_series(db, today, 6)
    budget_chart = _budget_chart_rows(budget_lines)
    equip_counts = Counter(e.status.value for e in equip)
    equip_chart = {
        "labels": list(equip_counts.keys()),
        "values": list(equip_counts.values()),
    }
    charts = {
        "trend": trend,
        "budget": budget_chart,
        "equipment": equip_chart,
        "paymentsMtd": float(Decimal(payments_mtd)),
    }
    chart_json = json.dumps(charts)
    subscription_count = SqlSubscriptionRepository(db).count_all()
    return render_page(
        request,
        "dashboard.html",
        title="Gösterge paneli",
        subscriber_count=len(subs),
        subscription_count=subscription_count,
        package_count=len(pkgs),
        equipment_count=len(equip),
        payments_mtd=payments_mtd,
        expiring_reports=expiring_reports,
        medical_horizon_end=horizon_end,
        today=today,
        chart_json=chart_json,
    )


@router.get("/ui/members", response_class=HTMLResponse)
def page_members(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    subs = SqlSubscriberRepository(db).list()
    reports = SqlMedicalReportRepository(db).list_all()
    cutoff = date.today() + timedelta(days=365)
    expiring = SqlMedicalReportRepository(db).list_expiring_before(cutoff)
    report_by_id = {r.id: r for r in reports if r.id is not None}
    pkg_by_id = {
        p.id: p
        for p in SqlSubscriptionPackageRepository(db).list()
        if p.id is not None
    }
    sub_repo = SqlSubscriptionRepository(db)
    member_subscriptions: dict[int, list[dict[str, Any]]] = {}
    for s in subs:
        if s.id is None:
            continue
        items: list[dict[str, Any]] = []
        for m in sub_repo.list_for_subscriber(s.id):
            if m.id is None or m.status != SubscriptionStatus.ACTIVE:
                continue
            items.append({"membership": m, "package": pkg_by_id.get(m.package_id)})
        member_subscriptions[s.id] = items
    return render_page(
        request,
        "members.html",
        title="Üyeler",
        subscribers=[s for s in subs if s.id is not None],
        reports=[r for r in reports if r.id is not None],
        expiring=[r for r in expiring if r.id is not None],
        report_by_id=report_by_id,
        member_subscriptions=member_subscriptions,
    )


@router.post("/ui/members/report")
def form_medical_report(
    institution_name: str = Form(...),
    issued_on: date = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    inst = institution_name.strip()
    if not inst:
        return _redirect("/ui/members", err="Kurum adı boş olamaz.")
    repo = SqlMedicalReportRepository(db)
    repo.add(MedicalReport(id=None, institution_name=inst, issued_on=issued_on))
    return _redirect("/ui/members", ok="1")


@router.post("/ui/members/subscriber")
def form_subscriber(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    medical_report_id: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    name = full_name.strip()
    em = email.strip()
    ph = phone.strip()
    if not name or not em or not ph:
        return _redirect("/ui/members", err="Tüm alanları doldurun.")
    rid: int | None = None
    if medical_report_id.strip():
        try:
            rid = int(medical_report_id)
        except ValueError:
            return _redirect("/ui/members", err="Geçersiz rapor numarası.")
        if SqlMedicalReportRepository(db).get(rid) is None:
            return _redirect("/ui/members", err="Rapor bulunamadı.")
    SqlSubscriberRepository(db).add(
        Subscriber(id=None, full_name=name, email=em, phone=ph, medical_report_id=rid)
    )
    return _redirect("/ui/members", ok="1")


@router.get("/ui/packages", response_class=HTMLResponse)
def page_packages(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    items = SqlSubscriptionPackageRepository(db).list()
    return render_page(
        request,
        "packages.html",
        title="Paketler",
        packages=[p for p in items if p.id is not None],
    )


@router.post("/ui/packages")
def form_create_package(
    name: str = Form(...),
    price: str = Form(...),
    kind: str = Form(...),
    billing_cycle_months: str = Form("1"),
    allowed_weekdays: str = Form(""),
    window_start: str = Form(""),
    window_end: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    nm = name.strip()
    if not nm:
        return _redirect("/ui/packages", err="Paket adı gerekli.")
    price_s = _parse_amount(price)
    if price_s is None:
        return _redirect("/ui/packages", err="Fiyat geçersiz.")
    try:
        kind_e = PackageKind(kind)
    except ValueError:
        return _redirect("/ui/packages", err="Paket türü geçersiz.")
    try:
        bcm = int(billing_cycle_months.strip() or "1")
    except ValueError:
        return _redirect("/ui/packages", err="Faturalama ayı geçersiz.")
    if bcm < 1 or bcm > 120:
        return _redirect("/ui/packages", err="Faturalama 1–120 ay arasında olmalı.")

    allowed: frozenset[int] | None = None
    ws: time | None = None
    we: time | None = None
    if kind_e in (PackageKind.FIXED_TWO_DAYS, PackageKind.FIXED_THREE_DAYS):
        raw = [p.strip() for p in allowed_weekdays.replace(",", " ").split() if p.strip()]
        days: list[int] = []
        for p in raw:
            try:
                d = int(p)
            except ValueError:
                return _redirect(
                    "/ui/packages",
                    err="Günler 0–6 arası tam sayılar olmalı (virgül veya boşlukla ayırın).",
                )
            if d < 0 or d > 6:
                return _redirect("/ui/packages", err="Gün 0=Pzt … 6=Paz aralığında olmalı.")
            days.append(d)
        if len(days) != len(set(days)):
            return _redirect("/ui/packages", err="Aynı gün iki kez yazılamaz.")
        allowed = frozenset(days)
    elif kind_e == PackageKind.DAILY_TIME_WINDOW:
        ws = _parse_time_hm(window_start)
        we = _parse_time_hm(window_end)
        if ws is None or we is None:
            return _redirect(
                "/ui/packages",
                err="Günlük pencere için başlangıç ve bitiş saati gerekli (HH:MM).",
            )

    try:
        package = create_subscription_package(
            id=None,
            name=nm,
            price_amount=price_s,
            kind=kind_e,
            billing_cycle_months=bcm,
            allowed_weekdays=allowed,
            window_start=ws,
            window_end=we,
        )
    except ValueError as exc:
        return _redirect("/ui/packages", err=str(exc))
    created = SqlSubscriptionPackageRepository(db).add(package)
    if created.id is None:
        return _redirect("/ui/packages", err="Paket kaydı tamamlanamadı.")
    return _redirect("/ui/packages", ok="1")


@router.get("/ui/subscriptions", response_class=HTMLResponse)
def page_subscriptions(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    today = date.today()
    subs = [s for s in SqlSubscriberRepository(db).list() if s.id is not None]
    pkgs = [p for p in SqlSubscriptionPackageRepository(db).list() if p.id is not None]
    pkg_by_id: dict[int, SubscriptionPackage] = {p.id: p for p in pkgs if p.id is not None}
    sub_repo = SqlSubscriptionRepository(db)
    pay_repo = SqlPaymentRepository(db)
    rows: list[dict[str, Any]] = []
    for sub in subs:
        for m in sub_repo.list_for_subscriber(sub.id):
            if m.id is None:
                continue
            pkg = pkg_by_id.get(m.package_id)
            end_d = m.end_date or today
            if end_d < m.start_date:
                end_d = m.start_date
            if pkg is None:
                periods, expected_s = 1, "0.00"
            else:
                periods, expected_s = subscription_expected_total(
                    pkg.price_amount,
                    m.start_date,
                    end_d,
                    pkg.billing_cycle_months,
                )
            total_paid = pay_repo.total_for_subscription(m.id)
            paid = Decimal(total_paid)
            expected = Decimal(expected_s)
            diff = (expected - paid).quantize(Decimal("0.01"))
            rows.append(
                {
                    "subscriber": sub,
                    "membership": m,
                    "package": pkg,
                    "billing_periods": periods,
                    "billing_label": _billing_cycle_label(pkg.billing_cycle_months) if pkg else "",
                    "expected_total": expected_s,
                    "total_paid": total_paid,
                    "remaining_due": str(diff) if diff > 0 else "",
                    "credit": str((-diff).quantize(Decimal("0.01"))) if diff < 0 else "",
                    "settled": diff == 0 and expected > 0,
                }
            )
    return render_page(
        request,
        "subscriptions.html",
        title="Abonelikler",
        subscribers=subs,
        packages=pkgs,
        rows=rows,
    )


@router.post("/ui/subscriptions/membership")
def form_membership(
    subscriber_id: int = Form(...),
    package_id: int = Form(...),
    start_date: date = Form(...),
    end_date: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if SqlSubscriberRepository(db).get(subscriber_id) is None:
        return _redirect("/ui/subscriptions", err="Üye bulunamadı.")
    if SqlSubscriptionPackageRepository(db).get(package_id) is None:
        return _redirect("/ui/subscriptions", err="Paket bulunamadı.")
    end: date | None = None
    if end_date.strip():
        try:
            end = date.fromisoformat(end_date.strip())
        except ValueError:
            return _redirect("/ui/subscriptions", err="Bitiş tarihi geçersiz.")
    SqlSubscriptionRepository(db).add(
        Subscription(
            id=None,
            subscriber_id=subscriber_id,
            package_id=package_id,
            start_date=start_date,
            end_date=end,
            status=SubscriptionStatus.ACTIVE,
        )
    )
    return _redirect("/ui/subscriptions", ok="1")


@router.post("/ui/subscriptions/{subscription_id}/pay")
def form_payment(
    subscription_id: int,
    amount: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if SqlSubscriptionRepository(db).get(subscription_id) is None:
        return _redirect("/ui/subscriptions", err="Abonelik bulunamadı.")
    amt = _parse_amount(amount)
    if amt is None:
        return _redirect("/ui/subscriptions", err="Geçersiz tutar.")
    paid_at = datetime.now()
    SqlPaymentRepository(db).add(
        Payment(
            id=None,
            subscription_id=subscription_id,
            amount=amt,
            paid_at=paid_at,
            note=note.strip() or None,
        )
    )
    SqlBudgetLineRepository(db).apply_subscription_payment_to_budget(paid_at, amt)
    return _redirect("/ui/subscriptions", ok="1")


def _equipment_page_item(
    e: Equipment,
    maintenance: list[MaintenanceRecord],
    repairs: list[RepairRecord],
) -> dict:
    maint_rows = [r for r in maintenance if r.id is not None]
    repair_rows = [r for r in repairs if r.id is not None]
    last_maint = max((r.performed_on for r in maint_rows), default=None)
    last_repair_sent = max((r.sent_on for r in repair_rows), default=None)
    return {
        "equipment": e,
        "maintenance": maintenance,
        "repairs": repairs,
        "maint_count": len(maint_rows),
        "repair_count": len(repair_rows),
        "last_maint": last_maint,
        "last_repair_sent": last_repair_sent,
    }


@router.get("/ui/equipment", response_class=HTMLResponse)
def page_equipment(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    equip = SqlEquipmentRepository(db).list()
    maint = SqlMaintenanceRepository(db)
    rep = SqlRepairRepository(db)
    items: list[dict] = []
    for e in equip:
        if e.id is None:
            continue
        mrows = maint.list_for_equipment(e.id)
        rrows = rep.list_for_equipment(e.id)
        items.append(_equipment_page_item(e, mrows, rrows))
    status_choices: list[tuple[str, str]] = [
        (EquipmentStatus.OPERATIONAL.value, "Çalışır durumda"),
        (EquipmentStatus.MAINTENANCE.value, "Salon bakımı / kontrol"),
        (EquipmentStatus.OUT_FOR_REPAIR.value, "Dış serviste"),
    ]
    status_counts: dict[str, int] = {EquipmentStatus.OPERATIONAL.value: 0, EquipmentStatus.MAINTENANCE.value: 0, EquipmentStatus.OUT_FOR_REPAIR.value: 0}
    for it in items:
        st = it["equipment"].status.value
        if st in status_counts:
            status_counts[st] += 1
    return render_page(
        request,
        "equipment.html",
        title="Ekipman",
        items=items,
        status_choices=status_choices,
        status_counts=status_counts,
    )


@router.post("/ui/equipment/new")
def form_equipment_new(
    name: str = Form(...),
    serial_number: str = Form(""),
    status: str = Form(EquipmentStatus.OPERATIONAL.value),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    nm = name.strip()
    if not nm:
        return _redirect("/ui/equipment", err="Ad gerekli.")
    try:
        st = EquipmentStatus(status)
    except ValueError:
        st = EquipmentStatus.OPERATIONAL
    SqlEquipmentRepository(db).add(
        Equipment(
            id=None,
            name=nm,
            serial_number=serial_number.strip() or None,
            status=st,
        )
    )
    return _redirect("/ui/equipment", ok="1")


@router.post("/ui/equipment/{equipment_id}/maintenance")
def form_maintenance(
    equipment_id: int,
    performed_on: date = Form(...),
    cost: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if SqlEquipmentRepository(db).get(equipment_id) is None:
        raise HTTPException(status_code=404)
    c = _parse_amount(cost)
    if c is None:
        return _redirect("/ui/equipment", err="Bakım maliyeti geçersiz.")
    desc = description.strip()
    if not desc:
        return _redirect("/ui/equipment", err="Açıklama gerekli.")
    SqlMaintenanceRepository(db).add(
        MaintenanceRecord(
            id=None,
            equipment_id=equipment_id,
            performed_on=performed_on,
            cost_amount=c,
            description=desc,
        )
    )
    return _redirect("/ui/equipment", ok="1")


@router.post("/ui/equipment/{equipment_id}/repair")
def form_repair(
    equipment_id: int,
    service_vendor: str = Form(...),
    sent_on: date = Form(...),
    returned_on: str = Form(""),
    cost: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if SqlEquipmentRepository(db).get(equipment_id) is None:
        raise HTTPException(status_code=404)
    c = _parse_amount(cost)
    if c is None:
        return _redirect("/ui/equipment", err="Tamir maliyeti geçersiz.")
    vendor = service_vendor.strip()
    if not vendor:
        return _redirect("/ui/equipment", err="Servis adı gerekli.")
    desc = description.strip()
    if not desc:
        return _redirect("/ui/equipment", err="Açıklama gerekli.")
    ret: date | None = None
    if returned_on.strip():
        try:
            ret = date.fromisoformat(returned_on.strip())
        except ValueError:
            return _redirect("/ui/equipment", err="İade tarihi geçersiz.")
    SqlRepairRepository(db).add(
        RepairRecord(
            id=None,
            equipment_id=equipment_id,
            service_vendor=vendor,
            sent_on=sent_on,
            returned_on=ret,
            cost_amount=c,
            description=desc,
        )
    )
    return _redirect("/ui/equipment", ok="1")


@router.get("/ui/budget", response_class=HTMLResponse)
def page_budget(
    request: Request,
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    today = date.today()
    y = year or today.year
    m = month or today.month
    lines = SqlBudgetLineRepository(db).list_period(y, m)
    cats = list(BudgetCategory)
    return render_page(
        request,
        "budget.html",
        title="Bütçe",
        year=y,
        month=m,
        lines=[ln for ln in lines if ln.id is not None],
        categories=cats,
    )


@router.post("/ui/budget/line")
def form_budget_line(
    period_year: int = Form(...),
    period_month: int = Form(...),
    category: str = Form(...),
    planned: str = Form(...),
    actual: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        cat = BudgetCategory(category)
    except ValueError:
        return _redirect("/ui/budget", err="Geçersiz kategori.")
    pl = _parse_amount(planned)
    ac = _parse_amount(actual)
    if pl is None or ac is None:
        return _redirect("/ui/budget", err="Tutarlar geçersiz.")
    SqlBudgetLineRepository(db).upsert(
        BudgetLine(
            id=None,
            period_year=period_year,
            period_month=period_month,
            category=cat,
            planned_amount=pl,
            actual_amount=ac,
        )
    )
    return _redirect(f"/ui/budget?year={period_year}&month={period_month}", ok="1")


@router.get("/ui/reports", response_class=HTMLResponse)
def page_reports(
    request: Request,
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    today = date.today()
    # Default: son 120 gün — demo verisi ay başı–bugün penceresinde sık sık dışarıda kalıyordu
    default_start = today - timedelta(days=120)
    s = start if start is not None else default_start
    e = end if end is not None else today
    if s > e:
        s, e = e, s
    maint = SqlMaintenanceRepository(db).total_cost_between(s, e)
    repair = SqlRepairRepository(db).total_cost_between(s, e)
    totals_empty = Decimal(maint) == 0 and Decimal(repair) == 0
    return render_page(
        request,
        "reports.html",
        title="Maliyet raporu",
        start=s,
        end=e,
        maintenance_total=maint,
        repair_total=repair,
        totals_empty=totals_empty,
    )
