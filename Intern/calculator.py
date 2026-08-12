import datetime
from typing import List, Tuple
from pydantic import BaseModel, Field

class DelayItem(BaseModel):
    reason: str
    duration: float  # hours

class CalculationRequest(BaseModel):
    vessel_name: str = "Vessel"
    cargo_type: str  # finished_product, crude, fuel_oil
    berth_type: str  # DTB, SPBM
    laycan_start: datetime.date
    laycan_end: datetime.date
    arrival_time: datetime.datetime
    nor_tendered: datetime.datetime
    nor_accepted: datetime.datetime
    loading_arm_disconnected: datetime.datetime
    terminal_requested_early: bool = False
    terminal_granted_permission_late: bool = False
    berths_count: int = 1
    vessel_delays: List[DelayItem] = []
    terminal_delays: List[DelayItem] = []

class CalculationResponse(BaseModel):
    actual_elapsed_hours: float
    laycan_start_time: datetime.datetime
    rule_applied: str
    allowed_laytime_hours: float
    shifting_deduction_hours: float
    total_vessel_delays_hours: float
    total_terminal_delays_hours: float
    net_vessel_delays_hours: float
    net_terminal_delays_hours: float
    operational_time_hours: float
    demurrage_hours: float
    demurrage_payable: bool

def calculate_laycan_start(
    berth_type: str,
    laycan_start: datetime.date,
    laycan_end: datetime.date,
    arrival_time: datetime.datetime,
    nor_accepted: datetime.datetime,
    terminal_requested_early: bool,
    terminal_granted_permission_late: bool
) -> Tuple[datetime.datetime, str]:
    """
    Calculates the laycan start datetime and returns a descriptive string of the rule applied.
    All incoming datetimes should be treated as local/naive.
    """
    arrival_date = arrival_time.date()
    
    # Rule 1: Arrival BEFORE the laycan window
    if arrival_date < laycan_start:
        if terminal_requested_early:
            rule = "Rule 1(i): Vessel arrived before laycan window; terminal requested early start. Laycan starts at NOR Accepted time."
            return nor_accepted, rule
        else:
            if berth_type == "DTB":
                start_dt = datetime.datetime.combine(laycan_start, datetime.time(13, 0))
                rule = "Rule 1(ii): Vessel arrived before laycan window at DTB. Terminal did not request early start. Laycan starts at 13:00 on the first day of laycan."
                return start_dt, rule
            else:  # SPBM
                start_dt = datetime.datetime.combine(laycan_start, datetime.time(12, 0))
                rule = "Rule 1(ii): Vessel arrived before laycan window at SPBM. Terminal did not request early start. Laycan starts at 12:00 on the first day of laycan."
                return start_dt, rule

    # Rule 2 & 3: Arrival DURING the laycan window
    elif laycan_start <= arrival_date <= laycan_end:
        arrival_hour = arrival_time.time()
        
        if berth_type == "DTB":
            cutoff = datetime.time(17, 0)
            if arrival_hour > cutoff:
                if terminal_granted_permission_late:
                    rule = "Rule 2/3: Vessel arrived after 17:00 at DTB during laycan. Terminal granted permission. Laycan starts at NOR Accepted time."
                    return nor_accepted, rule
                else:
                    next_day = arrival_date + datetime.timedelta(days=1)
                    start_dt = datetime.datetime.combine(next_day, datetime.time(13, 0))
                    rule = "Rule 2/3: Vessel arrived after 17:00 at DTB during laycan. No early permission. Laycan starts at 13:00 on the next day."
                    return start_dt, rule
            else:
                rule = "Rule 2/3: Vessel arrived before 17:00 at DTB during laycan. Laycan starts at NOR Accepted time."
                return nor_accepted, rule
                
        else:  # SPBM
            cutoff = datetime.time(15, 0)
            if arrival_hour > cutoff:
                if terminal_granted_permission_late:
                    rule = "Rule 2/3: Vessel arrived after 15:00 at SPBM during laycan. Terminal granted permission. Laycan starts at NOR Accepted time."
                    return nor_accepted, rule
                else:
                    next_day = arrival_date + datetime.timedelta(days=1)
                    start_dt = datetime.datetime.combine(next_day, datetime.time(12, 0))
                    rule = "Rule 2/3: Vessel arrived after 15:00 at SPBM during laycan. No early permission. Laycan starts at 12:00 on the next day."
                    return start_dt, rule
            else:
                rule = "Rule 2/3: Vessel arrived before 15:00 at SPBM during laycan. Laycan starts at NOR Accepted time."
                return nor_accepted, rule

    # Rule 4: Arrival AFTER the laycan window
    else:
        rule = "Rule 4: Vessel arrived after the laycan window. Laycan starts at NOR Accepted time."
        return nor_accepted, rule

def run_calculation(req: CalculationRequest) -> CalculationResponse:
    # 1. Calculate laycan start time
    laycan_start_time, rule_applied = calculate_laycan_start(
        berth_type=req.berth_type,
        laycan_start=req.laycan_start,
        laycan_end=req.laycan_end,
        arrival_time=req.arrival_time,
        nor_accepted=req.nor_accepted,
        terminal_requested_early=req.terminal_requested_early,
        terminal_granted_permission_late=req.terminal_granted_permission_late
    )

    # 2. Get allowed laytime
    allowed_map = {
        "finished_product": 96.0,
        "crude": 72.0,
        "fuel_oil": 120.0
    }
    allowed_laytime_hours = allowed_map.get(req.cargo_type, 96.0)

    # 3. Calculate actual elapsed hours
    # Make sure we don't end up with negative values if inputs are weird
    actual_elapsed_seconds = (req.loading_arm_disconnected - laycan_start_time).total_seconds()
    actual_elapsed_hours = max(0.0, actual_elapsed_seconds / 3600.0)

    # 4. Shifting deduction ("shifty")
    shifting_deduction_hours = 4.0 if req.berths_count >= 2 else 0.0

    # 5. Delay sums and netting
    total_vessel_delays_hours = sum(d.duration for d in req.vessel_delays)
    total_terminal_delays_hours = sum(d.duration for d in req.terminal_delays)

    net_vessel_delays_hours = max(0.0, total_vessel_delays_hours - total_terminal_delays_hours)
    net_terminal_delays_hours = max(0.0, total_terminal_delays_hours - total_vessel_delays_hours)

    # 6. Operational time calculation
    # Operational time is actual elapsed time minus shifting deduction and net vessel delay.
    # Note: Terminal delays are not deducted, they are just noted.
    operational_time_hours = max(0.0, actual_elapsed_hours - shifting_deduction_hours - net_vessel_delays_hours)

    # 7. Demurrage hours and payable
    demurrage_hours = max(0.0, operational_time_hours - allowed_laytime_hours)
    demurrage_payable = demurrage_hours > 0.0

    return CalculationResponse(
        actual_elapsed_hours=round(actual_elapsed_hours, 2),
        laycan_start_time=laycan_start_time,
        rule_applied=rule_applied,
        allowed_laytime_hours=allowed_laytime_hours,
        shifting_deduction_hours=shifting_deduction_hours,
        total_vessel_delays_hours=round(total_vessel_delays_hours, 2),
        total_terminal_delays_hours=round(total_terminal_delays_hours, 2),
        net_vessel_delays_hours=round(net_vessel_delays_hours, 2),
        net_terminal_delays_hours=round(net_terminal_delays_hours, 2),
        operational_time_hours=round(operational_time_hours, 2),
        demurrage_hours=round(demurrage_hours, 2),
        demurrage_payable=demurrage_payable
    )
