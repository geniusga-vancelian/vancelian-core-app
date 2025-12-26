"""
Tests for /api/v1/offers endpoint (list offers)
"""
import pytest
from fastapi.testclient import TestClient

from app.core.users.models import User
from app.core.offers.models import Offer, OfferStatus
from decimal import Decimal


def test_list_offers_returns_200_with_token(client: TestClient, test_user: User, db_session):
    """
    Test that list_offers returns 200 with valid token and returns JSON list
    """
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Create a LIVE offer for testing
    offer = db_session.query(Offer).filter(Offer.status == OfferStatus.LIVE).first()
    if not offer:
        offer = Offer(
            code="TEST-OFFER-LIST",
            name="Test Offer for List",
            currency="AED",
            max_amount=Decimal("100000.00"),
            invested_amount=Decimal("0.00"),
            committed_amount=Decimal("0.00"),
            status=OfferStatus.LIVE,
        )
        db_session.add(offer)
        db_session.commit()
    
    # Call list_offers
    response = client.get(
        "/api/v1/offers?status=LIVE&currency=AED&limit=50&offset=0",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:3000",  # Include Origin to test CORS
        },
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify response is a list
    assert isinstance(data, list), "Response should be a list"
    
    # Verify CORS headers are present
    assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()] or \
           "Access-Control-Allow-Origin" in response.headers, \
           f"CORS headers should be present. Headers: {list(response.headers.keys())}"
    
    # If offers exist, verify structure
    if len(data) > 0:
        offer_data = data[0]
        assert "id" in offer_data
        assert "code" in offer_data
        assert "name" in offer_data
        assert "status" in offer_data
        assert offer_data["status"] == "LIVE", "Only LIVE offers should be returned"


def test_list_offers_returns_400_for_invalid_status(client: TestClient, test_user: User, db_session):
    """
    Test that list_offers returns 400 with proper JSON format for invalid status
    """
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Call with invalid status
    response = client.get(
        "/api/v1/offers?status=INVALID&currency=AED",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:3000",
        },
    )
    
    assert response.status_code == 400, f"Expected 400 for invalid status, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify error format
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "trace_id" in data["error"]
    assert data["error"]["code"] == "INVALID_STATUS"
    
    # Verify CORS headers are present even on error
    assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()] or \
           "Access-Control-Allow-Origin" in response.headers, \
           "CORS headers should be present even on error responses"


def test_list_offers_always_returns_json_on_error(client: TestClient, test_user: User, db_session):
    """
    Test that list_offers always returns JSON error format, never raw stack traces
    """
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Call list_offers (should succeed or return JSON error, never raw HTML/stack trace)
    response = client.get(
        "/api/v1/offers?currency=AED",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:3000",
        },
    )
    
    # Response should be JSON (even if error)
    assert response.headers.get("content-type", "").startswith("application/json"), \
           f"Response should be JSON, got content-type: {response.headers.get('content-type')}"
    
    # Should be able to parse as JSON
    try:
        data = response.json()
        # If error, should have structured format
        if response.status_code >= 400:
            assert "error" in data or "detail" in data, \
                   f"Error response should have error/detail: {data}"
    except Exception as e:
        pytest.fail(f"Response should be valid JSON, but got: {response.text[:200]}")


def test_list_offers_cors_headers(client: TestClient, test_user: User, db_session):
    """
    Test that CORS headers are present when Origin header is sent
    """
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Call without Origin (CORS headers may not be present)
    response_no_origin = client.get(
        "/api/v1/offers?currency=AED",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Call with Origin (CORS headers should be present)
    response_with_origin = client.get(
        "/api/v1/offers?currency=AED",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:3000",
        },
    )
    
    # With Origin, CORS headers should be present
    assert "access-control-allow-origin" in [h.lower() for h in response_with_origin.headers.keys()] or \
           "Access-Control-Allow-Origin" in response_with_origin.headers, \
           "CORS headers should be present when Origin header is sent"

