"""Örnek veri: ilk kurulumda SQLite'u örnek kayıtlarla doldurur (sıfırdan)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gym_management.domain.equipment.equipment import Equipment, EquipmentStatus
from gym_management.domain.equipment.maintenance_record import MaintenanceRecord
from gym_management.domain.equipment.repair_record import RepairRecord
from gym_management.domain.finance.budget import BudgetCategory, BudgetLine
from gym_management.domain.finance.payment import Payment
from gym_management.domain.membership.medical_report import MedicalReport
from gym_management.domain.membership.subscriber import Subscriber
from gym_management.domain.subscription.package_factory import create_subscription_package
from gym_management.domain.subscription.schedule_strategy import PackageKind
from gym_management.domain.subscription.subscription import Subscription, SubscriptionStatus
from gym_management.domain.subscription.subscription_package import SubscriptionPackage
from gym_management.infrastructure.database import get_session_factory
from gym_management.infrastructure.orm_models import SubscriptionPackageRow
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


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def _add_months(d: date, months: int) -> date:
    m0 = d.month - 1 + months
    year = d.year + m0 // 12
    month = m0 % 12 + 1
    cap = _last_day_of_month(year, month)
    day = min(d.day, cap)
    return date(year, month, day)


def _payment_days(start: date, end: date, step_months: int = 1) -> list[date]:
    """Ödeme tarihleri; ilk ödeme başlangıçtan ~1 hafta sonra, sonra her ``step_months`` ay."""
    out: list[date] = []
    step = max(1, step_months)
    d = start + timedelta(days=7)
    while d <= end:
        out.append(d)
        d = _add_months(d, step)
    return out


def seed_if_empty() -> None:
    factory = get_session_factory()
    session = factory()
    try:
        count = session.scalar(select(func.count()).select_from(SubscriptionPackageRow)) or 0
        if int(count) > 0:
            return
        today = date.today()
        packages = _seed_packages(session)
        reports = _seed_medical_reports(session, today)
        subscribers = _seed_subscribers(session, reports, today)
        _seed_subscriptions_and_payments(session, subscribers, packages, today)
        _seed_equipment_and_costs(session, today)
        _seed_budget(session, today)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _seed_packages(session: Session) -> list[SubscriptionPackage]:
    repo = SqlSubscriptionPackageRepository(session)
    catalog = [
        create_subscription_package(
            id=None,
            name="Aylık — Haftada 2 Gün (Pzt/Perş)",
            price_amount="899.00",
            billing_cycle_months=1,
            kind=PackageKind.FIXED_TWO_DAYS,
            allowed_weekdays=frozenset({0, 3}),
        ),
        create_subscription_package(
            id=None,
            name="Aylık — Haftada 3 Gün",
            price_amount="1199.00",
            billing_cycle_months=1,
            kind=PackageKind.FIXED_THREE_DAYS,
            allowed_weekdays=frozenset({1, 3, 5}),
        ),
        create_subscription_package(
            id=None,
            name="Aylık — Her Gün Akşam (17–21)",
            price_amount="1499.00",
            billing_cycle_months=1,
            kind=PackageKind.DAILY_TIME_WINDOW,
            window_start=time(17, 0),
            window_end=time(21, 0),
        ),
        create_subscription_package(
            id=None,
            name="Aylık — Haftada 2 Gün (Sal/Cts)",
            price_amount="949.00",
            billing_cycle_months=1,
            kind=PackageKind.FIXED_TWO_DAYS,
            allowed_weekdays=frozenset({1, 5}),
        ),
        create_subscription_package(
            id=None,
            name="3 Aylık — Her Gün Akşam (17–21)",
            price_amount="4199.00",
            billing_cycle_months=3,
            kind=PackageKind.DAILY_TIME_WINDOW,
            window_start=time(17, 0),
            window_end=time(21, 0),
        ),
        create_subscription_package(
            id=None,
            name="3 Aylık — Haftada 3 Gün",
            price_amount="3299.00",
            billing_cycle_months=3,
            kind=PackageKind.FIXED_THREE_DAYS,
            allowed_weekdays=frozenset({0, 2, 4}),
        ),
        create_subscription_package(
            id=None,
            name="6 Aylık — Haftada 3 Gün",
            price_amount="5999.00",
            billing_cycle_months=6,
            kind=PackageKind.FIXED_THREE_DAYS,
            allowed_weekdays=frozenset({1, 3, 5}),
        ),
        create_subscription_package(
            id=None,
            name="Yıllık — Her Gün Akşam (17–21)",
            price_amount="14499.00",
            billing_cycle_months=12,
            kind=PackageKind.DAILY_TIME_WINDOW,
            window_start=time(17, 0),
            window_end=time(21, 0),
        ),
    ]
    return [repo.add(p) for p in catalog]


def _seed_medical_reports(session: Session, today: date) -> list[MedicalReport]:
    repo = SqlMedicalReportRepository(session)
    specs = [
        ("Çankaya Aile Sağlığı Merkezi", today - timedelta(days=90)),
        ("Özel Mediva Hastanesi", today - timedelta(days=340)),
        ("Özgün Poliklinik", today - timedelta(days=40)),
        ("Başkent Üniversitesi Hastanesi", today - timedelta(days=180)),
        ("Liv Hospital Ankara", today - timedelta(days=25)),
        ("Medicana International", today - timedelta(days=200)),
        ("TOBB ETÜ Sağlık Merkezi", today - timedelta(days=310)),
        ("Koru Sağlık Grubu", today - timedelta(days=72)),
        ("Gazi Üniversitesi Hastanesi", today - timedelta(days=410)),
        ("Bayındır Hastanesi", today - timedelta(days=5)),
        ("Medicalpark Ankara", today - timedelta(days=150)),
        ("Diş Hekimliği — Özel Ağız Diş", today - timedelta(days=120)),
    ]
    return [repo.add(MedicalReport(id=None, institution_name=n, issued_on=d)) for n, d in specs]


def _seed_subscribers(
    session: Session, reports: list[MedicalReport], today: date
) -> list[Subscriber]:
    repo = SqlSubscriberRepository(session)
    rids = [r.id for r in reports]
    specs = [
        ("Ayşe Yılmaz", "ayse.yilmaz@sportifposta.com", "0532 111 2233", rids[0]),
        ("Mehmet Kaya", "mehmet.kaya@sportifposta.com", "0533 444 5566", rids[1]),
        ("Zehra Demir", "zehra.demir@sportifposta.com", "0534 777 8899", rids[2]),
        ("Can Öztürk", "can.ozturk@posta.gen.tr", "0535 000 1122", None),
        ("Elif Arslan", "elif.arslan@sportifposta.com", "0536 222 3344", rids[3]),
        ("Burak Şahin", "burak.sahin@sportifposta.com", "0537 555 6677", rids[4]),
        ("Deniz Koç", "deniz.koc@posta.gen.tr", "0538 888 9900", rids[5]),
        ("Selin Aydın", "selin.aydin@sportifposta.com", "0539 121 3434", None),
        ("Emre Çelik", "emre.celik@sportifposta.com", "0540 454 7878", rids[6]),
        ("Melis Yurt", "melis.yurt@sportifposta.com", "0541 787 1212", rids[7]),
        ("Kerem Polat", "kerem.polat@posta.gen.tr", "0542 010 4545", rids[8]),
        ("İrem Güneş", "irem.gunes@sportifposta.com", "0543 343 7878", rids[9]),
        ("Ozan Tekin", "ozan.tekin@sportifposta.com", "0544 676 0101", rids[10]),
        ("Ceren Bozkurt", "ceren.bozkurt@sportifposta.com", "0545 909 3434", rids[11]),
        ("Hakan Kurt", "hakan.kurt@posta.gen.tr", "0546 232 6767", None),
        ("Aslı Erdoğan", "asli.erdogan@sportifposta.com", "0547 565 9090", rids[0]),
    ]
    out: list[Subscriber] = []
    for name, email, phone, mr in specs:
        out.append(
            repo.add(
                Subscriber(
                    id=None,
                    full_name=name,
                    email=email,
                    phone=phone,
                    medical_report_id=mr,
                )
            )
        )
    return out


def _seed_subscriptions_and_payments(
    session: Session,
    subscribers: list[Subscriber],
    packages: list[SubscriptionPackage],
    today: date,
) -> None:
    sub_repo = SqlSubscriptionRepository(session)
    pay_repo = SqlPaymentRepository(session)
    cycle_by_pkg_id = {p.id: p.billing_cycle_months for p in packages if p.id is not None}
    price_by_pkg_id = {p.id: p.price_amount for p in packages if p.id is not None}
    if not price_by_pkg_id:
        return

    def pay_schedule(subscription_id: int, package_id: int, start: date, end: date) -> None:
        if subscription_id is None:
            return
        step = cycle_by_pkg_id.get(package_id, 1)
        days = _payment_days(start, end, step)
        for i, pay_day in enumerate(days):
            base = price_by_pkg_id.get(package_id, "0.00")
            amt = base
            pay_repo.add(
                Payment(
                    id=None,
                    subscription_id=subscription_id,
                    amount=amt,
                    paid_at=datetime.combine(pay_day, datetime.min.time()),
                    note=f"Geçmiş abonelik ödemesi {i + 1}",
                )
            )

    history: list[tuple[int, int, date, date, SubscriptionStatus]] = [
        (0, 0, today - timedelta(days=280), today - timedelta(days=160), SubscriptionStatus.EXPIRED),
        (1, 1, today - timedelta(days=200), today - timedelta(days=90), SubscriptionStatus.EXPIRED),
        (2, 2, today - timedelta(days=150), today - timedelta(days=45), SubscriptionStatus.CANCELLED),
        (3, 3, today - timedelta(days=120), today - timedelta(days=60), SubscriptionStatus.EXPIRED),
    ]
    for si, pi, sd, ed, status in history:
        s, p = subscribers[si], packages[pi]
        if s.id is None or p.id is None:
            continue
        m = sub_repo.add(
            Subscription(
                id=None,
                subscriber_id=s.id,
                package_id=p.id,
                start_date=sd,
                end_date=ed,
                status=status,
            )
        )
        pay_schedule(m.id, p.id, sd, ed)

    for i, s in enumerate(subscribers):
        if s.id is None:
            continue
        p = packages[i % len(packages)]
        if p.id is None:
            continue
        sd = today - timedelta(days=12 + (i * 9) % 95)
        m = sub_repo.add(
            Subscription(
                id=None,
                subscriber_id=s.id,
                package_id=p.id,
                start_date=sd,
                end_date=None,
                status=SubscriptionStatus.ACTIVE,
            )
        )
        if m.id is None:
            continue
        days = _payment_days(sd, today, p.billing_cycle_months)
        for j, pay_day in enumerate(days):
            base = Decimal(price_by_pkg_id[p.id])
            if i == 5 and j == 1:
                amt = "600.00"
            elif i == 11 and j == 0:
                amt = str((base * Decimal("0.5")).quantize(Decimal("0.01")))
            else:
                amt = str(base.quantize(Decimal("0.01")))
            pay_repo.add(
                Payment(
                    id=None,
                    subscription_id=m.id,
                    amount=amt,
                    paid_at=datetime.combine(pay_day, datetime.min.time()),
                    note=f"Aktif paket ödeme {j + 1}",
                )
            )


def _seed_equipment_and_costs(session: Session, today: date) -> None:
    equip_repo = SqlEquipmentRepository(session)
    maint_repo = SqlMaintenanceRepository(session)
    repair_repo = SqlRepairRepository(session)

    items: list[tuple[str, str | None, EquipmentStatus]] = [
        ("Koşu bandı — Kardiyo A", "TRD-2023-014", EquipmentStatus.OPERATIONAL),
        ("Koşu bandı — Kardiyo B", "TRD-2023-019", EquipmentStatus.OPERATIONAL),
        ("Spin bisiklet — Grup ders", "SPN-2022-008", EquipmentStatus.MAINTENANCE),
        ("Eliptik bisiklet — Zone 2", "ELP-2021-019", EquipmentStatus.OPERATIONAL),
        ("Kürek ergometre", "ROW-2023-006", EquipmentStatus.OUT_FOR_REPAIR),
        ("Smith makinesi — Ağırlık holü", "SMT-2021-003", EquipmentStatus.OPERATIONAL),
        ("Leg press — 45°", "LGP-2023-021", EquipmentStatus.OPERATIONAL),
        ("Hack squat", "HKS-2022-004", EquipmentStatus.OPERATIONAL),
        ("Cable crossover — Çift istasyon", "DBL-2022-015", EquipmentStatus.OPERATIONAL),
        ("Lat pulldown / seated row — Kule", "LAT-2020-031", EquipmentStatus.OPERATIONAL),
        ("Pec deck — Uçan", "PEC-2019-012", EquipmentStatus.OPERATIONAL),
        ("Omuz presi — PL yüklemeli", "SHP-2021-007", EquipmentStatus.OPERATIONAL),
        ("Ayarlanabilir bench — 12 kademe", "BNC-2024-002", EquipmentStatus.OPERATIONAL),
        ("Roman chair — Bel / karın", "ROM-2018-005", EquipmentStatus.OPERATIONAL),
        ("Power rack — Çekme çubuğu", "PWK-2023-011", EquipmentStatus.OPERATIONAL),
        ("Dips / bacak kaldırma istasyonu", "DIP-2020-009", EquipmentStatus.OPERATIONAL),
        ("TRX / fonksiyonel askı istasyonu", "TRX-2019-001", EquipmentStatus.OPERATIONAL),
        ("Dambıl rafı — 1–40 kg set", "DBR-2024-003", EquipmentStatus.OPERATIONAL),
    ]
    equipment: list[Equipment] = []
    for name, serial, status in items:
        equipment.append(
            equip_repo.add(
                Equipment(id=None, name=name, serial_number=serial, status=status)
            )
        )

    maint_specs: list[tuple[int, date, str, str]] = [
        (0, today - timedelta(days=14), "450.00", "Periyodik kontrol ve yağlama"),
        (0, today - timedelta(days=75), "890.00", "Koşu bandı kayış gerginliği ayarı"),
        (1, today - timedelta(days=22), "380.00", "Motor fanı temizliği"),
        (2, today - timedelta(days=7), "380.00", "Fren balatası ve kalibrasyon"),
        (3, today - timedelta(days=45), "520.00", "Eğim motoru kontrol"),
        (4, today - timedelta(days=10), "290.00", "Sensör ve ray temizliği"),
        (5, today - timedelta(days=21), "520.00", "Gözden geçirme ve sıvı kontrolü"),
        (6, today - timedelta(days=120), "890.00", "Hidrolik silindir kontrolü"),
        (7, today - timedelta(days=200), "340.00", "Kayar ray gresi"),
        (8, today - timedelta(days=45), "610.00", "Kablo ve makara incelemesi"),
        (9, today - timedelta(days=95), "425.00", "Halat ve tutamak kontrolü"),
        (10, today - timedelta(days=60), "290.00", "Kam ve mil yağlama"),
        (11, today - timedelta(days=110), "510.00", "Yük pimleri ve stop kontrolü"),
        (12, today - timedelta(days=90), "340.00", "Minder ve menteşe ayarı"),
        (13, today - timedelta(days=130), "275.00", "Pedalı somun sıkma"),
        (14, today - timedelta(days=40), "410.00", "J-hook ve güvenlik kolu"),
        (15, today - timedelta(days=18), "225.00", "Tutamaç lastik değişimi"),
        (16, today - timedelta(days=55), "350.00", "Tavan ankraj gerilim testi"),
        (17, today - timedelta(days=8), "180.00", "Raf etiketleri ve düzen"),
    ]
    for eq_idx, performed_on, cost, desc in maint_specs:
        e = equipment[eq_idx]
        if e.id is None:
            continue
        maint_repo.add(
            MaintenanceRecord(
                id=None,
                equipment_id=e.id,
                performed_on=performed_on,
                cost_amount=cost,
                description=desc,
            )
        )

    repair_specs: list[tuple[int, str, date, date | None, str, str]] = [
        (
            2,
            "Arena Teknik Servis A.Ş.",
            today - timedelta(days=21),
            today - timedelta(days=7),
            "2850.00",
            "Elektronik kart ve direnç motoru revizyonu",
        ),
        (
            4,
            "CardioCare Ankara",
            today - timedelta(days=40),
            None,
            "4200.00",
            "Şanzıman ve manyetik fren; parça beklemede",
        ),
        (
            6,
            "StrongLine Servis",
            today - timedelta(days=5),
            today + timedelta(days=9),
            "1650.00",
            "Hidrolik kaçak ve conta değişimi",
        ),
        (
            8,
            "GymTeknik Ltd.",
            today - timedelta(days=95),
            today - timedelta(days=78),
            "980.00",
            "Kablo kanalı ve emniyet stopu",
        ),
        (
            1,
            "Arena Teknik Servis A.Ş.",
            today - timedelta(days=180),
            today - timedelta(days=165),
            "1120.00",
            "Bütünleşik motor testi ve yazılım güncellemesi",
        ),
    ]
    for eq_idx, vendor, sent_on, returned_on, cost, desc in repair_specs:
        e = equipment[eq_idx]
        if e.id is None:
            continue
        repair_repo.add(
            RepairRecord(
                id=None,
                equipment_id=e.id,
                service_vendor=vendor,
                sent_on=sent_on,
                returned_on=returned_on,
                cost_amount=cost,
                description=desc,
            )
        )


def _seed_budget(session: Session, today: date) -> None:
    year, month = today.year, today.month
    start_d, month_end = _month_end_bounds(year, month)
    pay_repo = SqlPaymentRepository(session)
    mtd_start = datetime.combine(start_d, datetime.min.time())
    mtd_end = datetime.combine(
        date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1),
        datetime.min.time(),
    )
    sub_actual = pay_repo.total_between(mtd_start, mtd_end)

    maint_repo = SqlMaintenanceRepository(session)
    maint_actual = maint_repo.total_cost_between(start_d, month_end)

    repair_repo = SqlRepairRepository(session)
    repair_actual = repair_repo.total_cost_between(start_d, month_end)

    repo = SqlBudgetLineRepository(session)
    lines = [
        BudgetLine(
            id=None,
            period_year=year,
            period_month=month,
            category=BudgetCategory.SUBSCRIPTION_REVENUE,
            planned_amount="220000.00",
            actual_amount=sub_actual,
        ),
        BudgetLine(
            id=None,
            period_year=year,
            period_month=month,
            category=BudgetCategory.MAINTENANCE_EXPENSE,
            planned_amount="18000.00",
            actual_amount=maint_actual,
        ),
        BudgetLine(
            id=None,
            period_year=year,
            period_month=month,
            category=BudgetCategory.REPAIR_EXPENSE,
            planned_amount="20000.00",
            actual_amount=repair_actual,
        ),
    ]
    for line in lines:
        repo.upsert(line)


def _month_end_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year, month, _last_day_of_month(year, month))
    return start, end
