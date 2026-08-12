import os
import pytest
import datetime
from db import (
    init_db,
    create_user,
    delete_user,
    list_users,
    create_session,
    validate_session,
    delete_session,
    save_calculation,
    get_calculations,
    delete_calculation,
    verify_password
)

TEST_DB = "test_demurrage.db"

@pytest.fixture(autouse=True)
def setup_teardown_db():
    # Setup: remove any existing test db
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    # Teardown: remove test db
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_user_creation_and_auth():
    # 1. Verify admin was seeded
    users = list_users(TEST_DB)
    assert len(users) == 1
    assert users[0]['username'] == 'admin'
    assert users[0]['role'] == 'admin'

    # 2. Create a new user
    success = create_user("testuser", "testpassword", "user", TEST_DB)
    assert success is True
    
    # Try creating duplicate
    duplicate = create_user("testuser", "anotherpwd", "user", TEST_DB)
    assert duplicate is False

    # 3. Check list of users
    users = list_users(TEST_DB)
    assert len(users) == 2
    assert users[1]['username'] == 'testuser'
    assert users[1]['role'] == 'user'

    # 4. Verify deletion
    deleted = delete_user("testuser", TEST_DB)
    assert deleted is True
    users = list_users(TEST_DB)
    assert len(users) == 1

    # Cannot delete main admin
    deleted_admin = delete_user("admin", TEST_DB)
    assert deleted_admin is False

def test_session_handling():
    # Create session for admin
    token = create_session("admin", TEST_DB)
    assert token is not None
    assert len(token) == 48  # 24 bytes in hex is 48 chars

    # Validate session
    session = validate_session(token, TEST_DB)
    assert session is not None
    assert session['username'] == 'admin'
    assert session['role'] == 'admin'

    # Delete session
    delete_session(token, TEST_DB)
    session = validate_session(token, TEST_DB)
    assert session is None

def test_calculations_crud():
    create_user("john", "johnpassword", "user", TEST_DB)
    
    req_data = {
        "vessel_name": "Test Vessel",
        "cargo_type": "finished_product",
        "berth_type": "DTB",
        "laycan_start": "2026-08-15",
        "laycan_end": "2026-08-17",
        "arrival_time": "2026-08-15T12:00:00",
        "nor_tendered": "2026-08-15T12:00:00",
        "nor_accepted": "2026-08-15T12:00:00",
        "loading_arm_disconnected": "2026-08-20T12:00:00",
        "terminal_requested_early": False,
        "terminal_granted_permission_late": False,
        "berths_count": 1,
        "vessel_delays": [],
        "terminal_delays": []
    }
    
    res_data = {
        "actual_elapsed_hours": 120.0,
        "laycan_start_time": "2026-08-15T12:00:00",
        "rule_applied": "Rule 2/3...",
        "allowed_laytime_hours": 96.0,
        "shifting_deduction_hours": 0.0,
        "total_vessel_delays_hours": 0.0,
        "total_terminal_delays_hours": 0.0,
        "net_vessel_delays_hours": 0.0,
        "net_terminal_delays_hours": 0.0,
        "operational_time_hours": 120.0,
        "demurrage_hours": 24.0,
        "demurrage_payable": True
    }
    
    # Save calculation
    calc_id = save_calculation("john", req_data, res_data, TEST_DB)
    assert calc_id > 0

    # Retrieve calculations for john
    john_calcs = get_calculations("john", "user", TEST_DB)
    assert len(john_calcs) == 1
    assert john_calcs[0]['vessel_name'] == "Test Vessel"
    assert john_calcs[0]['result']['demurrage_hours'] == 24.0

    # Retrieve calculations for admin (should see all)
    admin_calcs = get_calculations("admin", "admin", TEST_DB)
    assert len(admin_calcs) == 1

    # Delete calculation as non-owner (should fail or affect 0 rows)
    deleted_by_other = delete_calculation(calc_id, "admin_fake_user", "user", TEST_DB)
    assert deleted_by_other is False

    # Delete calculation as owner
    deleted_by_owner = delete_calculation(calc_id, "john", "user", TEST_DB)
    assert deleted_by_owner is True

    john_calcs = get_calculations("john", "user", TEST_DB)
    assert len(john_calcs) == 0
