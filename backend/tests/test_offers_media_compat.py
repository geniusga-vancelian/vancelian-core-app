"""
Tests for offers media backward compatibility (sort_order, created_at optional)
"""
import pytest
from fastapi.testclient import TestClient
from decimal import Decimal
from datetime import datetime, timezone

from app.core.users.models import User
from app.core.offers.models import Offer, OfferStatus, OfferMedia, MediaType, MediaVisibility


def test_list_offers_with_media_missing_fields(client: TestClient, test_user: User, db_session):
    """
    Test that list_offers returns 200 even when media items don't have sort_order/created_at
    """
    # Create token
    from app.api.v1.auth import create_access_token
    token = create_access_token(test_user.id, test_user.email)
    
    # Create a LIVE offer
    offer = db_session.query(Offer).filter(Offer.status == OfferStatus.LIVE).first()
    if not offer:
        offer = Offer(
            code="TEST-OFFER-MEDIA-COMPAT",
            name="Test Offer Media Compat",
            currency="AED",
            max_amount=Decimal("100000.00"),
            invested_amount=Decimal("0.00"),
            committed_amount=Decimal("0.00"),
            status=OfferStatus.LIVE,
        )
        db_session.add(offer)
        db_session.flush()
    
    # Create a media item (will have sort_order=0 and created_at from BaseModel)
    media = db_session.query(OfferMedia).filter(
        OfferMedia.offer_id == offer.id,
        OfferMedia.visibility == MediaVisibility.PUBLIC
    ).first()
    
    if not media:
        media = OfferMedia(
            offer_id=offer.id,
            type=MediaType.IMAGE,
            key=f"test-media-{offer.id}",
            mime_type="image/jpeg",
            size_bytes=1024,
            width=800,
            height=600,
            sort_order=0,  # Has sort_order
            is_cover=False,
            visibility=MediaVisibility.PUBLIC,
        )
        db_session.add(media)
        db_session.commit()
    
    # Call list_offers
    response = client.get(
        "/api/v1/offers?status=LIVE&currency=AED&limit=50&offset=0",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "http://localhost:3000",
        },
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    # Verify response is a list
    assert isinstance(data, list), "Response should be a list"
    
    # Find our offer in the response
    offer_data = next((o for o in data if o.get("code") == offer.code), None)
    if offer_data:
        # Verify media structure exists
        assert "media" in offer_data or "cover_url" in offer_data, "Offer should have media or cover_url"
        
        # If media block exists, verify structure
        if "media" in offer_data and offer_data["media"]:
            # Check that media items have sort_order (default 0) and created_at (can be None)
            for media_item in offer_data["media"]:
                assert "sort_order" in media_item, "Media item should have sort_order"
                assert media_item["sort_order"] is not None, "sort_order should not be None (defaults to 0)"
                # created_at can be None for backward compatibility
                if "created_at" in media_item:
                    # If present, should be a string (ISO format) or None
                    assert media_item["created_at"] is None or isinstance(media_item["created_at"], str), \
                           "created_at should be None or ISO string"


def test_media_item_response_defaults(client: TestClient, test_user: User, db_session):
    """
    Test that MediaItemResponse uses default values for sort_order and created_at when not provided
    """
    from app.schemas.offers import MediaItemResponse
    
    # Create MediaItemResponse with minimal fields (simulating old data)
    media_item = MediaItemResponse(
        id="123e4567-e89b-12d3-a456-426614174000",
        type="IMAGE",
        mime_type="image/jpeg",
        size_bytes=1024,
        url="https://example.com/image.jpg",
    )
    
    # Verify defaults are applied
    assert media_item.sort_order == 0, "sort_order should default to 0"
    assert media_item.is_cover == False, "is_cover should default to False"
    assert media_item.created_at is None, "created_at should default to None"
    
    # Verify it can be serialized to JSON
    json_data = media_item.model_dump()
    assert json_data["sort_order"] == 0
    assert json_data["is_cover"] == False
    assert json_data["created_at"] is None


def test_document_item_response_defaults(client: TestClient, test_user: User, db_session):
    """
    Test that DocumentItemResponse uses default value for created_at when not provided
    """
    from app.schemas.offers import DocumentItemResponse
    
    # Create DocumentItemResponse with minimal fields (simulating old data)
    document_item = DocumentItemResponse(
        id="123e4567-e89b-12d3-a456-426614174001",
        name="test-document.pdf",
        kind="BROCHURE",
        mime_type="application/pdf",
        size_bytes=2048,
        url="https://example.com/document.pdf",
    )
    
    # Verify default is applied
    assert document_item.created_at is None, "created_at should default to None"
    
    # Verify it can be serialized to JSON
    json_data = document_item.model_dump()
    assert json_data["created_at"] is None

