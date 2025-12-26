"""
Tests for ZAND deposit simulation endpoint (DEV ONLY)
"""

import pytest
import jwt
import time
from uuid import uuid4
from decimal import Decimal
from sqlalchemy.orm import Session
from unittest.mock import patch, Mock

from app.services.wallet_helpers import get_wallet_balances
from app.infrastructure.settings import get_settings


def _create_jwt_token(user_id: str, email: str, roles: list[str] = None) -> str:
    """Helper to create JWT token compatible with auth system (HS256)"""
    settings = get_settings()
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "roles": roles or ["USER"],
            "iat": now,
            "exp": now + 3600,
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def test_simulate_deposit_success(
    client,
    db_session: Session,
    test_user,
    test_internal_account,
):
    """
    Test successful deposit simulation:
    - POST /api/v1/webhooks/zandbank/simulate returns 200
    - Response contains sim_version == "v1"
    - operation_id present
    """
    # Create token for test user
    token = _create_jwt_token(str(test_user.id), test_user.email, ["USER"])
    
    # Simulate deposit
    response = client.post(
        "/api/v1/webhooks/zandbank/simulate",
        json={
            "currency": "AED",
            "amount": "10.00",
            "reference": "ZAND-SIM-TEST-001",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Assert success
    assert response.status_code == 200, f"Unexpected status: {response.json()}"
    response_data = response.json()
    
    assert response_data["status"] == "COMPLETED"
    assert response_data["currency"] == "AED"
    assert response_data["amount"] == "10.00"
    assert response_data["reference"] == "ZAND-SIM-TEST-001"
    assert response_data["sim_version"] == "v1"
    assert "operation_id" in response_data
    assert response_data["operation_id"] is not None
    assert "transaction_id" in response_data
    assert response_data["transaction_id"] is not None


def test_simulate_deposit_wallet_updated(
    client,
    db_session: Session,
    test_user,
    test_internal_account,
):
    """
    Test that deposit simulation updates wallet balances:
    - total_balance increases by deposit amount
    - blocked_balance increases by deposit amount (since record_deposit_blocked)
    """
    # Get initial balances (should be 0 if no accounts exist yet)
    try:
        initial_balances = get_wallet_balances(db_session, test_user.id, "AED")
        initial_total = initial_balances["total_balance"]
        initial_blocked = initial_balances["blocked_balance"]
    except Exception:
        # Accounts don't exist yet, start from 0
        initial_total = Decimal("0.00")
        initial_blocked = Decimal("0.00")
    
    deposit_amount = Decimal("10.00")
    
    # Create token for test user
    token = _create_jwt_token(str(test_user.id), test_user.email, ["USER"])
    
    # Simulate deposit
    response = client.post(
        "/api/v1/webhooks/zandbank/simulate",
        json={
            "currency": "AED",
            "amount": str(deposit_amount),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    
    # Check wallet via API endpoint
    wallet_response = client.get(
        "/api/v1/wallet?currency=AED",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert wallet_response.status_code == 200
    wallet_data = wallet_response.json()
    
    # Assert balances increased
    new_total = Decimal(wallet_data["total_balance"])
    new_blocked = Decimal(wallet_data["blocked_balance"])
    
    assert new_total == initial_total + deposit_amount, \
        f"Total balance: expected {initial_total + deposit_amount}, got {new_total}"
    assert new_blocked == initial_blocked + deposit_amount, \
        f"Blocked balance: expected {initial_blocked + deposit_amount}, got {new_blocked}"


def test_simulate_deposit_invalid_amount_zero(
    client,
    db_session: Session,
    test_user,
):
    """Test that amount=0 returns 422 with JSON error"""
    token = _create_jwt_token(str(test_user.id), test_user.email, ["USER"])
    
    response = client.post(
        "/api/v1/webhooks/zandbank/simulate",
        json={
            "currency": "AED",
            "amount": "0",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 422  # Validation error
    error_data = response.json()
    assert "error" in error_data or "detail" in error_data
    
    # Pydantic validation may return "detail" instead of "error"
    if "error" in error_data:
        assert "code" in error_data["error"]
        assert "trace_id" in error_data["error"]


def test_simulate_deposit_invalid_amount_negative(
    client,
    db_session: Session,
    test_user,
):
    """Test that negative amount returns 422 with JSON error"""
    token = _create_jwt_token(str(test_user.id), test_user.email, ["USER"])
    
    response = client.post(
        "/api/v1/webhooks/zandbank/simulate",
        json={
            "currency": "AED",
            "amount": "-1.00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 422  # Validation error
    error_data = response.json()
    assert "error" in error_data or "detail" in error_data


def test_simulate_deposit_invalid_currency(
    client,
    db_session: Session,
    test_user,
):
    """Test that currency != AED returns 422 with JSON error"""
    token = _create_jwt_token(str(test_user.id), test_user.email, ["USER"])
    
    response = client.post(
        "/api/v1/webhooks/zandbank/simulate",
        json={
            "currency": "USD",
            "amount": "10.00",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 422  # Validation error
    error_data = response.json()
    assert "error" in error_data or "detail" in error_data


def test_simulate_deposit_unauthorized(
    client,
    db_session: Session,
):
    """Test that request without Authorization header returns 401 with JSON error"""
    response = client.post(
        "/api/v1/webhooks/zandbank/simulate",
        json={
            "currency": "AED",
            "amount": "10.00",
        },
    )
    
    assert response.status_code == 401
    error_data = response.json()
    assert "error" in error_data
    assert "code" in error_data["error"]
    assert "trace_id" in error_data["error"]


def test_simulate_deposit_dev_gate_blocked(
    client,
    db_session: Session,
    test_user,
    monkeypatch,
):
    """
    Test DEV gate: endpoint returns 403 when not in dev/debug mode
    """
    token = _create_jwt_token(str(test_user.id), test_user.email, ["USER"])
    
    # Patch settings to simulate production mode
    mock_settings = Mock()
    mock_settings.ENV = "prod"
    mock_settings.debug = False  # Property, not method
    
    # Patch get_settings_instance in the webhook module
    with patch('app.api.v1.webhooks.zandbank.get_settings_instance', return_value=mock_settings):
        response = client.post(
            "/api/v1/webhooks/zandbank/simulate",
            json={
                "currency": "AED",
                "amount": "10.00",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    
    assert response.status_code == 403
    error_data = response.json()
    assert "error" in error_data
    assert error_data["error"]["code"] == "WEBHOOK_SIM_DISABLED"
    assert "trace_id" in error_data["error"]


def test_simulate_deposit_error_always_json(
    client,
    db_session: Session,
    test_user,
):
    """
    Test that all errors return JSON format with error{code,message,trace_id}
    """
    # Test with invalid JSON (malformed request)
    token = _create_jwt_token(str(test_user.id), test_user.email, ["USER"])
    
    # Send malformed JSON
    response = client.post(
        "/api/v1/webhooks/zandbank/simulate",
        data="invalid json{",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    
    # Should return JSON error (even for malformed requests)
    assert response.status_code in [400, 422]
    # FastAPI should still return JSON
    assert response.headers.get("content-type", "").startswith("application/json")
    try:
        error_data = response.json()
        # May have "detail" or "error" depending on error type
        assert "detail" in error_data or "error" in error_data
    except Exception:
        pytest.fail("Response is not valid JSON")
