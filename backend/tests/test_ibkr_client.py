import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest # Using pytest for its features like fixtures and async support

# Adjust the import path based on your project structure
# This assumes tests are run from the root directory or backend/
from backend.ibkr_client import IBKRClient
# If running pytest from root, path might be 'backend.ibkr_client'
# If pytest is run from backend/, it might be 'ibkr_client'

# Fixture for IBKRClient instance
@pytest.fixture
def client():
    return IBKRClient()

@pytest.mark.asyncio
async def test_ibkr_client_connect_success(client):
    # Mock ib_insync.IB instance and its connectAsync method
    mock_ib_instance = AsyncMock()
    mock_ib_instance.isConnected.return_value = False # Initially not connected

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance) as mock_ib_class:
        # Re-initialize client to use the patched IB
        test_client = IBKRClient()
        connected = await test_client.connect()

        assert connected is True
        assert test_client.is_connected is True
        mock_ib_instance.connectAsync.assert_called_once_with(test_client.host, test_client.port, test_client.client_id)
        # mock_ib_instance.run.assert_called_once() # If connectAsync triggers a run

@pytest.mark.asyncio
async def test_ibkr_client_connect_already_connected(client):
    mock_ib_instance = MagicMock() # Using MagicMock as connectAsync won't be called
    mock_ib_instance.isConnected.return_value = True # Already connected

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance):
        test_client = IBKRClient() # Client is initialized with mocked IB
        # Correct way to test this: client.connect() should set client.is_connected to True
        # if ib.isConnected() is True.
        # The client's own self.is_connected is an internal state reflecting its *belief*
        # or the result of the last operation.

        # Scenario: IB says it's connected.
        connected = await test_client.connect()

        assert connected is True
        assert test_client.is_connected is True # Should be true after successful "connection" (even if no actual call)
        mock_ib_instance.connectAsync.assert_not_called()

@pytest.mark.asyncio
async def test_ibkr_client_connect_failure(client):
    mock_ib_instance = AsyncMock()
    mock_ib_instance.isConnected.return_value = False
    mock_ib_instance.connectAsync.side_effect = ConnectionRefusedError("Test connection refused")

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance):
        test_client = IBKRClient()
        connected = await test_client.connect()

        assert connected is False
        assert test_client.is_connected is False
        mock_ib_instance.connectAsync.assert_called_once()

@pytest.mark.asyncio
async def test_ibkr_client_disconnect(client):
    mock_ib_instance = MagicMock()
    mock_ib_instance.isConnected.return_value = True # Assume IB reports it's connected

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance) as mock_ib_class:
        test_client = IBKRClient()
        # To test disconnect, the client should believe it's connected.
        # This happens if a connect() call was successful.
        # Let's simulate this by setting is_connected, assuming connect() was called.
        test_client.is_connected = True

        await test_client.disconnect()

        assert test_client.is_connected is False
        mock_ib_instance.disconnect.assert_called_once()

@pytest.mark.asyncio
async def test_get_portfolio_success(client):
    mock_ib_instance = AsyncMock()
    # Simulate that connect() will be called and will succeed
    mock_ib_instance.isConnected.side_effect = [False, True] # First call for connect(), second for subsequent checks if any

    mock_contract = MagicMock(symbol="AAPL", secType="STK")
    mock_portfolio_item = MagicMock(contract=mock_contract, position=100, marketPrice=150.0)
    mock_ib_instance.portfolioAsync.return_value = [mock_portfolio_item]

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance):
        test_client = IBKRClient()
        portfolio = await test_client.get_portfolio()

        assert len(portfolio) == 1
        assert portfolio[0].contract.symbol == "AAPL"
        mock_ib_instance.connectAsync.assert_called_once()
        mock_ib_instance.portfolioAsync.assert_called_once()

@pytest.mark.asyncio
async def test_get_positions_success(client):
    mock_ib_instance = AsyncMock()
    mock_ib_instance.isConnected.side_effect = [False, True] # For connect() call

    mock_contract = MagicMock(symbol="TSLA", secType="STK")
    mock_position = MagicMock(contract=mock_contract, position=50, avgCost=200.0, account="U123")
    mock_ib_instance.positionsAsync.return_value = [mock_position]

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance):
        test_client = IBKRClient()
        positions = await test_client.get_positions()

        assert len(positions) == 1
        assert positions[0].contract.symbol == "TSLA"
        assert positions[0].account == "U123"
        mock_ib_instance.connectAsync.assert_called_once()
        mock_ib_instance.positionsAsync.assert_called_once()

def test_ibkr_client_initialization_defaults(client):
    # This test uses the fixture 'client' which is already initialized
    # It will use environment variables if set, or defaults if not.
    # To test defaults specifically, we should ensure env vars are not set for this test.
    with patch.dict(os.environ, {}, clear=True): # Clear relevant IBKR env vars
        default_client = IBKRClient()
        assert default_client.host == '127.0.0.1'
        assert default_client.port == 7497
        assert default_client.client_id == 1

def test_ibkr_client_initialization_from_env_vars():
    with patch.dict(os.environ, {'IBKR_HOST': 'testhost', 'IBKR_PORT': '1234', 'IBKR_CLIENT_ID': '99'}):
        env_client = IBKRClient()
        assert env_client.host == 'testhost'
        assert env_client.port == 1234
        assert env_client.client_id == 99

@pytest.mark.asyncio
async def test_get_portfolio_connection_fails(client):
    mock_ib_instance = AsyncMock()
    mock_ib_instance.isConnected.return_value = False
    mock_ib_instance.connectAsync.side_effect = ConnectionRefusedError("Failed to connect")

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance):
        test_client = IBKRClient()
        portfolio = await test_client.get_portfolio()
        assert portfolio == []
        mock_ib_instance.portfolioAsync.assert_not_called()

# Add more tests:
# - get_portfolio returning empty list from IB
# - get_positions returning empty list from IB
# - get_account_summary (if its implementation is firmed up)
# - Error handling within get_portfolio/get_positions if connect succeeds but API call fails
# - Test for util.startLoop() calls if loop is not running (more complex to set up mock for get_event_loop)

# Example test for util.startLoop() in get_portfolio
@pytest.mark.asyncio
async def test_get_portfolio_starts_event_loop_if_not_running(client):
    mock_ib_instance = AsyncMock()
    mock_ib_instance.isConnected.side_effect = [False, True]
    mock_ib_instance.portfolioAsync.return_value = []

    # Mock asyncio.get_event_loop() and util.startLoop()
    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance):
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = False # Simulate loop not running
            mock_get_loop.return_value = mock_loop

            with patch('backend.ibkr_client.util.startLoop') as mock_start_loop:
                test_client = IBKRClient()
                await test_client.get_portfolio()
                mock_start_loop.assert_called_once()

@pytest.mark.asyncio
async def test_get_positions_starts_event_loop_if_not_running(client):
    mock_ib_instance = AsyncMock()
    mock_ib_instance.isConnected.side_effect = [False, True]
    mock_ib_instance.positionsAsync.return_value = []

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance):
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = False
            mock_get_loop.return_value = mock_loop

            with patch('backend.ibkr_client.util.startLoop') as mock_start_loop:
                test_client = IBKRClient()
                await test_client.get_positions()
                mock_start_loop.assert_called_once()

@pytest.mark.asyncio
async def test_get_account_summary_starts_event_loop_if_not_running(client):
    mock_ib_instance = AsyncMock()
    mock_ib_instance.isConnected.side_effect = [False, True]
    # Mock accountValues to prevent actual calls if summary logic is complex
    mock_ib_instance.accountValues.return_value = []

    with patch('backend.ibkr_client.IB', return_value=mock_ib_instance):
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = False
            mock_get_loop.return_value = mock_loop

            with patch('backend.ibkr_client.util.startLoop') as mock_start_loop:
                test_client = IBKRClient()
                await test_client.get_account_summary()
                # This assertion depends on whether get_account_summary itself calls util.startLoop()
                # Based on current ibkr_client.py, it does.
                mock_start_loop.assert_called_once()
