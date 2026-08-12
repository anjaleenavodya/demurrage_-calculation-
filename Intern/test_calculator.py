import datetime
import pytest
from Intern.calculator import (
    CalculationRequest,
    DelayItem,
    calculate_laycan_start,
    run_calculation
)

def test_early_arrival_dtb():
    # Vessel arrives BEFORE laycan start date (Aug 15) on Aug 14 at 10:00
    laycan_start = datetime.date(2026, 8, 15)
    laycan_end = datetime.date(2026, 8, 17)
    arrival_time = datetime.datetime(2026, 8, 14, 10, 0)
    nor_tendered = datetime.datetime(2026, 8, 14, 10, 15)
    nor_accepted = datetime.datetime(2026, 8, 14, 11, 0)
    
    # 1. No early request: should start next day (first day of laycan) at 13:00
    start_dt, rule = calculate_laycan_start(
        berth_type="DTB",
        laycan_start=laycan_start,
        laycan_end=laycan_end,
        arrival_time=arrival_time,
        nor_accepted=nor_accepted,
        terminal_requested_early=False,
        terminal_granted_permission_late=False
    )
    assert start_dt == datetime.datetime(2026, 8, 15, 13, 0)
    assert "Rule 1(ii)" in rule

    # 2. Terminal requested early: should start at NOR accepted
    start_dt_early, rule_early = calculate_laycan_start(
        berth_type="DTB",
        laycan_start=laycan_start,
        laycan_end=laycan_end,
        arrival_time=arrival_time,
        nor_accepted=nor_accepted,
        terminal_requested_early=True,
        terminal_granted_permission_late=False
    )
    assert start_dt_early == nor_accepted
    assert "Rule 1(i)" in rule_early

def test_early_arrival_spbm():
    # Vessel arrives BEFORE laycan start date (Aug 15) on Aug 14 at 10:00
    laycan_start = datetime.date(2026, 8, 15)
    laycan_end = datetime.date(2026, 8, 17)
    arrival_time = datetime.datetime(2026, 8, 14, 10, 0)
    nor_accepted = datetime.datetime(2026, 8, 14, 11, 0)
    
    # No early request: should start next day (first day of laycan) at 12:00
    start_dt, rule = calculate_laycan_start(
        berth_type="SPBM",
        laycan_start=laycan_start,
        laycan_end=laycan_end,
        arrival_time=arrival_time,
        nor_accepted=nor_accepted,
        terminal_requested_early=False,
        terminal_granted_permission_late=False
    )
    assert start_dt == datetime.datetime(2026, 8, 15, 12, 0)
    assert "Rule 1(ii)" in rule

def test_during_laycan_dtb_before_cutoff():
    # Vessel arrives on Aug 15 (first day) at 16:30 (before 17:00)
    laycan_start = datetime.date(2026, 8, 15)
    laycan_end = datetime.date(2026, 8, 17)
    arrival_time = datetime.datetime(2026, 8, 15, 16, 30)
    nor_accepted = datetime.datetime(2026, 8, 15, 17, 30)
    
    start_dt, rule = calculate_laycan_start(
        berth_type="DTB",
        laycan_start=laycan_start,
        laycan_end=laycan_end,
        arrival_time=arrival_time,
        nor_accepted=nor_accepted,
        terminal_requested_early=False,
        terminal_granted_permission_late=False
    )
    assert start_dt == nor_accepted
    assert "before 17:00" in rule

def test_during_laycan_dtb_after_cutoff():
    # Vessel arrives on Aug 15 (first day) at 18:00 (after 17:00)
    laycan_start = datetime.date(2026, 8, 15)
    laycan_end = datetime.date(2026, 8, 17)
    arrival_time = datetime.datetime(2026, 8, 15, 18, 0)
    nor_accepted = datetime.datetime(2026, 8, 15, 19, 0)
    
    # 1. No late permission: starts next day (Aug 16) at 13:00
    start_dt, rule = calculate_laycan_start(
        berth_type="DTB",
        laycan_start=laycan_start,
        laycan_end=laycan_end,
        arrival_time=arrival_time,
        nor_accepted=nor_accepted,
        terminal_requested_early=False,
        terminal_granted_permission_late=False
    )
    assert start_dt == datetime.datetime(2026, 8, 16, 13, 0)
    assert "No early permission" in rule or "next day" in rule

    # 2. With late permission: starts at NOR accepted
    start_dt_perm, rule_perm = calculate_laycan_start(
        berth_type="DTB",
        laycan_start=laycan_start,
        laycan_end=laycan_end,
        arrival_time=arrival_time,
        nor_accepted=nor_accepted,
        terminal_requested_early=False,
        terminal_granted_permission_late=True
    )
    assert start_dt_perm == nor_accepted
    assert "Terminal granted permission" in rule_perm

def test_during_laycan_spbm_after_cutoff():
    # Vessel arrives on Aug 15 (first day) at 15:30 (after 15:00)
    laycan_start = datetime.date(2026, 8, 15)
    laycan_end = datetime.date(2026, 8, 17)
    arrival_time = datetime.datetime(2026, 8, 15, 15, 30)
    nor_accepted = datetime.datetime(2026, 8, 15, 16, 30)
    
    # No late permission: starts next day at 12:00
    start_dt, rule = calculate_laycan_start(
        berth_type="SPBM",
        laycan_start=laycan_start,
        laycan_end=laycan_end,
        arrival_time=arrival_time,
        nor_accepted=nor_accepted,
        terminal_requested_early=False,
        terminal_granted_permission_late=False
    )
    assert start_dt == datetime.datetime(2026, 8, 16, 12, 0)

def test_after_laycan():
    # Vessel arrives on Aug 18 (after laycan window Aug 15 - Aug 17)
    laycan_start = datetime.date(2026, 8, 15)
    laycan_end = datetime.date(2026, 8, 17)
    arrival_time = datetime.datetime(2026, 8, 18, 10, 0)
    nor_accepted = datetime.datetime(2026, 8, 18, 12, 0)
    
    start_dt, rule = calculate_laycan_start(
        berth_type="DTB",
        laycan_start=laycan_start,
        laycan_end=laycan_end,
        arrival_time=arrival_time,
        nor_accepted=nor_accepted,
        terminal_requested_early=False,
        terminal_granted_permission_late=False
    )
    assert start_dt == nor_accepted
    assert "after the laycan window" in rule

def test_run_calculation():
    # Complete calculation run with shifting and delay netting
    # Cargo: finished_product (96h allowed)
    # Laycan: Aug 15 - Aug 17
    # Arrival: Aug 15 at 12:00
    # NOR Accepted: Aug 15 at 12:00 (starts here, since DTB and arrival <= 17:00)
    # Disconnected: Aug 20 at 12:00
    # Elapsed = 5 days = 120 hours
    # Shifty (births_count=2) = -4h
    # Vessel delays = 10h
    # Terminal delays = 4h
    # Net vessel delays = 6h. Net terminal = 0h.
    # Operational time = 120h - 4h - 6h = 110h
    # Demurrage = 110h - 96h = 14h. Demurrage payable = True.
    req = CalculationRequest(
        vessel_name="Test Tanker",
        cargo_type="finished_product",
        berth_type="DTB",
        laycan_start=datetime.date(2026, 8, 15),
        laycan_end=datetime.date(2026, 8, 17),
        arrival_time=datetime.datetime(2026, 8, 15, 12, 0),
        nor_tendered=datetime.datetime(2026, 8, 15, 12, 0),
        nor_accepted=datetime.datetime(2026, 8, 15, 12, 0),
        loading_arm_disconnected=datetime.datetime(2026, 8, 20, 12, 0),
        terminal_requested_early=False,
        terminal_granted_permission_late=False,
        berths_count=2,
        vessel_delays=[DelayItem(reason="Vessel Pumping Issue", duration=10.0)],
        terminal_delays=[DelayItem(reason="Terminal Pumping Issue", duration=4.0)]
    )
    
    res = run_calculation(req)
    assert res.actual_elapsed_hours == 120.0
    assert res.shifting_deduction_hours == 4.0
    assert res.total_vessel_delays_hours == 10.0
    assert res.total_terminal_delays_hours == 4.0
    assert res.net_vessel_delays_hours == 6.0
    assert res.net_terminal_delays_hours == 0.0
    assert res.operational_time_hours == 110.0
    assert res.demurrage_hours == 14.0
    assert res.demurrage_payable is True
