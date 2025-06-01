from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
import pytest

# Adjust the import to your FastAPI app instance
from backend.main import app

client = TestClient(app)

@pytest.fixture
def mock_ibkr_sync_service():
    # Patch IBKRSyncService where it's imported/used in backend.main
    with patch('backend.main.IBKRSyncService', spec=True) as MockService:
        mock_instance = AsyncMock()
        MockService.return_value = mock_instance
        yield mock_instance

def test_trigger_ibkr_sync_success(mock_ibkr_sync_service):
    mock_ibkr_sync_service.sync_portfolio_positions.return_value = {
        "status": "success",
        "message": "IBKR portfolio sync completed.",
        "processed_items": 5,
        "new_items": 2,
        "updated_items": 3,
        "closed_in_db": 0,
        "errors": 0
    }

    response = client.post("/portfolio/sync/ibkr")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "success"
    assert json_response["new_items"] == 2
    mock_ibkr_sync_service.sync_portfolio_positions.assert_called_once_with(ibkr_account_id_filter=None)

def test_trigger_ibkr_sync_success_with_account_filter(mock_ibkr_sync_service):
    mock_ibkr_sync_service.sync_portfolio_positions.return_value = {
        "status": "success",
        "message": "IBKR portfolio sync completed for account U123.",
        "processed_items": 3,
        "new_items": 1,
        "updated_items": 2,
        "closed_in_db": 0,
        "errors": 0
    }

    account_id = "U123"
    response = client.post(f"/portfolio/sync/ibkr?ibkr_account_id={account_id}")

    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "success"
    assert "U123" in json_response["message"]
    mock_ibkr_sync_service.sync_portfolio_positions.assert_called_once_with(ibkr_account_id_filter=account_id)

def test_trigger_ibkr_sync_service_connection_error(mock_ibkr_sync_service):
    error_message = "Failed to connect to IBKR"
    # This simulates the dictionary returned by IBKRSyncService when its own connect() fails
    # or when it simply wants to report a critical error.
    mock_ibkr_sync_service.sync_portfolio_positions.return_value = {
        "status": "error",
        "message": error_message
    }

    response = client.post("/portfolio/sync/ibkr")

    # The endpoint should catch this "error" status and raise an HTTPException(500)
    assert response.status_code == 500
    json_response = response.json()
    assert json_response["detail"] == error_message
    mock_ibkr_sync_service.sync_portfolio_positions.assert_called_once()

def test_trigger_ibkr_sync_service_connection_refused_exception(mock_ibkr_sync_service):
    # This test simulates if the service's call to sync_portfolio_positions itself
    # raises a ConnectionRefusedError before it can return a dict.
    # The endpoint has a specific try-except for ConnectionRefusedError.
    error_message = "IBKR Connection Refused. Ensure TWS/Gateway is running and accessible."
    mock_ibkr_sync_service.sync_portfolio_positions.side_effect = ConnectionRefusedError(error_message)

    response = client.post("/portfolio/sync/ibkr")

    assert response.status_code == 503 # As per HTTPException in main.py for ConnectionRefusedError
    json_response = response.json()
    assert json_response["detail"] == error_message
    mock_ibkr_sync_service.sync_portfolio_positions.assert_called_once()


def test_trigger_ibkr_sync_service_unexpected_exception(mock_ibkr_sync_service):
    # Simulates an unexpected error during the service call.
    original_error_message = "Some unexpected service layer error"
    mock_ibkr_sync_service.sync_portfolio_positions.side_effect = Exception(original_error_message)

    response = client.post("/portfolio/sync/ibkr")

    assert response.status_code == 500 # General fallback exception
    json_response = response.json()
    # The endpoint formats the message, so we check if the original error is part of it.
    assert f"An unexpected error occurred during IBKR sync: {original_error_message}" in json_response["detail"]
    mock_ibkr_sync_service.sync_portfolio_positions.assert_called_once()


def test_trigger_ibkr_sync_service_partial_error_reported_in_success(mock_ibkr_sync_service):
    # Simulate a successful completion status but with some errors processing items
    detailed_error_message = "Sync completed with some errors."
    mock_ibkr_sync_service.sync_portfolio_positions.return_value = {
        "status": "success",
        "message": detailed_error_message,
        "processed_items": 5,
        "new_items": 1,
        "updated_items": 2,
        "closed_in_db": 0,
        "errors": 2
    }

    response = client.post("/portfolio/sync/ibkr")

    assert response.status_code == 200 # Still 200 because overall status is "success"
    json_response = response.json()
    assert json_response["status"] == "success"
    assert json_response["errors"] == 2
    assert json_response["message"] == detailed_error_message
    mock_ibkr_sync_service.sync_portfolio_positions.assert_called_once()

# Consider adding a test for when ibkr_account_id is an empty string if that's handled differently,
# though typically Optional[str] means it's either a string or None.
# If query param is ?ibkr_account_id= then FastAPI usually treats it as an empty string.
# The service currently passes this string along.
# If IBKRSyncService treats empty string "" differently from None, that could be a service-level test.
# For the API, it just passes it through.

def test_trigger_ibkr_sync_empty_account_id_param(mock_ibkr_sync_service):
    mock_ibkr_sync_service.sync_portfolio_positions.return_value = {"status": "success"}

    response = client.post("/portfolio/sync/ibkr?ibkr_account_id=") # Empty string

    assert response.status_code == 200
    # FastAPI will pass "" (empty string) to the endpoint, which is then passed to the service.
    mock_ibkr_sync_service.sync_portfolio_positions.assert_called_once_with(ibkr_account_id_filter="")
