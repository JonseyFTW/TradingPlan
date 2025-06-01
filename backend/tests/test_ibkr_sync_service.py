import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch, call # Added call

import pytest
from sqlmodel import Session # For type hinting if needed, actual session will be mocked

# Adjust import paths as necessary
from backend.ibkr_sync_service import IBKRSyncService
from backend.models import PortfolioPosition
from backend.ibkr_client import IBKRClient # Required for spec in mock_ibkr_client

# Mock contract and position data structures
def create_mock_ib_contract(symbol="TEST", conId=0, secType="STK", currency="USD", exchange="SMART"):
    contract = MagicMock(spec=['symbol', 'conId', 'secType', 'currency', 'exchange'])
    contract.symbol = symbol
    contract.conId = conId
    contract.secType = secType
    contract.currency = currency
    contract.exchange = exchange
    return contract

def create_mock_ib_position(account="DU000000", contract=None, position=0, avgCost=0.0):
    if contract is None:
        contract = create_mock_ib_contract()
    pos = MagicMock(spec=['account', 'contract', 'position', 'avgCost'])
    pos.account = account
    pos.contract = contract
    pos.position = position
    pos.avgCost = avgCost
    return pos

@pytest.fixture
def mock_db_engine():
    engine = MagicMock()
    return engine

@pytest.fixture
def mock_session():
    session = MagicMock(spec=Session)
    session.exec.return_value.first.return_value = None
    session.exec.return_value.all.return_value = []
    return session

@pytest.fixture
def mock_ibkr_client_instance(): # Renamed to avoid confusion with the patcher
    client = AsyncMock(spec=IBKRClient)
    client.connect.return_value = True
    client.get_positions.return_value = []
    client.get_portfolio.return_value = []
    return client

@pytest.fixture
def sync_service_components(mock_db_engine, mock_session, mock_ibkr_client_instance):
    service = IBKRSyncService(db_engine=mock_db_engine)
    return service, mock_ibkr_client_instance, mock_session


@pytest.mark.asyncio
async def test_sync_portfolio_positions_connect_failure(sync_service_components, mock_session):
    service, mock_client, _ = sync_service_components
    mock_client.connect.return_value = False

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
      with patch('backend.ibkr_sync_service.Session', return_value=mock_session):
          result = await service.sync_portfolio_positions()

    assert result["status"] == "error"
    assert "Failed to connect to IBKR" in result["message"]
    mock_client.get_positions.assert_not_called()


@pytest.mark.asyncio
async def test_sync_new_position(sync_service_components, mock_session):
    service, mock_client, session_mock = sync_service_components # Use session_mock for clarity

    contract_data = create_mock_ib_contract(symbol="AAPL", conId=123, exchange="NASDAQ")
    ibkr_pos_data = [create_mock_ib_position(account="U123", contract=contract_data, position=100, avgCost=150.0)]
    mock_client.get_positions.return_value = ibkr_pos_data

    mock_find_existing_query = MagicMock()
    mock_find_existing_query.first.return_value = None

    mock_get_all_open_db_query = MagicMock()
    mock_get_all_open_db_query.all.return_value = []

    session_mock.exec.side_effect = [
        mock_find_existing_query,
        mock_get_all_open_db_query
    ]

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=session_mock):
            result = await service.sync_portfolio_positions(ibkr_account_id_filter="U123")

    assert result["status"] == "success"
    assert result["new_items"] == 1
    assert result["updated_items"] == 0
    assert result["closed_in_db"] == 0

    added_object = session_mock.add.call_args[0][0]
    assert isinstance(added_object, PortfolioPosition)
    assert added_object.symbol == "AAPL"
    assert added_object.quantity == 100
    assert added_object.ibkr_account_id == "U123"
    session_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sync_update_existing_position(sync_service_components, mock_session):
    service, mock_client, session_mock = sync_service_components

    existing_db_pos = PortfolioPosition(
        id=1, symbol="MSFT", quantity=50, entry_price=200.0,
        ibkr_account_id="U123", ibkr_con_id=456, status="OPEN",
        sec_type="STK", currency="USD", exchange="NASDAQ", entry_date=date(2023,1,1)
    )

    mock_query_result_existing = MagicMock()
    mock_query_result_existing.first.return_value = existing_db_pos

    contract_data = create_mock_ib_contract(symbol="MSFT", conId=456, exchange="NASDAQ")
    ibkr_pos_data = [create_mock_ib_position(account="U123", contract=contract_data, position=75, avgCost=205.0)]
    mock_client.get_positions.return_value = ibkr_pos_data

    mock_query_all_open_db = MagicMock()
    # This position is active in IBKR, so it should be in this list for the set comparison
    mock_query_all_open_db.all.return_value = [existing_db_pos]
    session_mock.exec.side_effect = [mock_query_result_existing, mock_query_all_open_db]

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=session_mock):
            result = await service.sync_portfolio_positions(ibkr_account_id_filter="U123")

    assert result["status"] == "success"
    assert result["new_items"] == 0
    assert result["updated_items"] == 1
    assert result["closed_in_db"] == 0

    assert existing_db_pos.quantity == 75
    assert existing_db_pos.entry_price == 205.0
    session_mock.add.assert_called_with(existing_db_pos)
    session_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sync_close_position_not_in_ibkr(sync_service_components, mock_session):
    service, mock_client, session_mock = sync_service_components

    db_pos_to_close = PortfolioPosition(
        id=2, symbol="GOOG", quantity=10, entry_price=1000.0,
        ibkr_account_id="U123", ibkr_con_id=789, status="OPEN",
        sec_type="STK", currency="USD", exchange="NASDAQ", entry_date=date(2023,1,1)
    )

    mock_client.get_positions.return_value = []

    mock_query_all_open_db = MagicMock()
    mock_query_all_open_db.all.return_value = [db_pos_to_close]
    session_mock.exec.return_value = mock_query_all_open_db # Only one exec call for .all()

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=session_mock):
            result = await service.sync_portfolio_positions(ibkr_account_id_filter="U123")

    assert result["status"] == "success"
    assert result["new_items"] == 0
    assert result["updated_items"] == 0
    assert result["closed_in_db"] == 1

    assert db_pos_to_close.status == "CLOSED"
    assert db_pos_to_close.quantity == 0
    assert db_pos_to_close.exit_date == date.today()
    session_mock.add.assert_called_with(db_pos_to_close)
    session_mock.commit.assert_called_once()

@pytest.mark.asyncio
async def test_sync_with_account_filter(sync_service_components, mock_session):
    service, mock_client, session_mock = sync_service_components

    contract1 = create_mock_ib_contract(symbol="AAPL", conId=1)
    pos1_acc1 = create_mock_ib_position(account="U123", contract=contract1, position=10, avgCost=100)

    contract2 = create_mock_ib_contract(symbol="MSFT", conId=2)
    pos2_acc2 = create_mock_ib_position(account="U456", contract=contract2, position=20, avgCost=200)

    mock_client.get_positions.return_value = [pos1_acc1, pos2_acc2]

    # Mock DB: U123 (AAPL) is new, U456 (MSFT) is irrelevant for this filter.
    # A position for U123 in DB that is not in IBKR should be closed.
    db_pos_acc1_to_close = PortfolioPosition(id=3, symbol="TSLA", ibkr_account_id="U123", ibkr_con_id=3, quantity=5, status="OPEN", entry_date=date(2023,1,1))

    mock_find_pos1_acc1 = MagicMock()
    mock_find_pos1_acc1.first.return_value = None # AAPL is new

    # For closing logic, only U123 positions are considered from DB
    mock_get_all_open_db_acc1 = MagicMock()
    mock_get_all_open_db_acc1.all.return_value = [db_pos_acc1_to_close]

    session_mock.exec.side_effect = [
        mock_find_pos1_acc1, # For AAPL in U123
        # No exec call for MSFT in U456 because of account filter in service's loop
        mock_get_all_open_db_acc1 # For closing logic, filtered by U123
    ]

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=session_mock):
            result = await service.sync_portfolio_positions(ibkr_account_id_filter="U123")

    assert result["status"] == "success"
    assert result["new_items"] == 1      # AAPL from U123 added
    assert result["updated_items"] == 0
    assert result["processed_items"] == 1 # Only AAPL from U123 processed
    assert result["closed_in_db"] == 1   # TSLA from U123 in DB closed

    # Check added object
    added_call = None
    updated_call = None
    closed_call = None
    for c in session_mock.add.call_args_list:
        obj = c[0][0]
        if obj.symbol == "AAPL":
            added_call = obj
        if obj.symbol == "TSLA": # This is the one that got closed
            closed_call = obj

    assert added_call is not None and added_call.symbol == "AAPL" and added_call.ibkr_account_id == "U123"
    assert closed_call is not None and closed_call.symbol == "TSLA" and closed_call.status == "CLOSED"

    session_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sync_no_account_filter(sync_service_components, mock_session):
    service, mock_client, session_mock = sync_service_components

    contract1 = create_mock_ib_contract(symbol="AAPL", conId=1)
    pos1_acc1 = create_mock_ib_position(account="U123", contract=contract1, position=10, avgCost=100)

    contract2 = create_mock_ib_contract(symbol="MSFT", conId=2)
    pos2_acc2 = create_mock_ib_position(account="U456", contract=contract2, position=20, avgCost=200) # New

    mock_client.get_positions.return_value = [pos1_acc1, pos2_acc2]

    # DB: AAPL (U123) exists and will be updated. MSFT (U456) is new.
    # A position (TSLA U789) in DB not in IBKR should be closed.
    db_pos_aapl_u123 = PortfolioPosition(id=1, symbol="AAPL", ibkr_account_id="U123", ibkr_con_id=1, quantity=5, entry_price=90, status="OPEN", entry_date=date(2023,1,1))
    db_pos_tsla_u789_to_close = PortfolioPosition(id=3, symbol="TSLA", ibkr_account_id="U789", ibkr_con_id=3, quantity=5, status="OPEN", entry_date=date(2023,1,1))

    mock_find_aapl = MagicMock()
    mock_find_aapl.first.return_value = db_pos_aapl_u123
    mock_find_msft = MagicMock()
    mock_find_msft.first.return_value = None # MSFT is new

    mock_get_all_open_db = MagicMock()
    mock_get_all_open_db.all.return_value = [db_pos_aapl_u123, db_pos_tsla_u789_to_close]

    session_mock.exec.side_effect = [
        mock_find_aapl, # For AAPL U123
        mock_find_msft, # For MSFT U456
        mock_get_all_open_db
    ]

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=session_mock):
            result = await service.sync_portfolio_positions(ibkr_account_id_filter=None) # No filter

    assert result["status"] == "success"
    assert result["new_items"] == 1      # MSFT U456
    assert result["updated_items"] == 1  # AAPL U123
    assert result["processed_items"] == 2 # Both processed
    assert result["closed_in_db"] == 1   # TSLA U789

    assert db_pos_aapl_u123.quantity == 10 # Check update

    added_symbol = ""
    for c_args in session_mock.add.call_args_list:
        obj = c_args[0][0]
        if obj.symbol == "MSFT":
            added_symbol = obj.symbol
        # We can also check that db_pos_aapl_u123 and db_pos_tsla_u789_to_close were arguments to add()

    assert added_symbol == "MSFT"
    assert db_pos_tsla_u789_to_close.status == "CLOSED"
    session_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sync_error_processing_one_position(sync_service_components, mock_session):
    service, mock_client, session_mock = sync_service_components

    contract_ok = create_mock_ib_contract(symbol="OK", conId=1)
    pos_ok = create_mock_ib_position(account="U123", contract=contract_ok, position=10, avgCost=100)

    # This position will cause an error because its 'position' attribute is not convertible to int directly
    contract_bad = create_mock_ib_contract(symbol="BAD", conId=2)
    pos_bad = create_mock_ib_position(account="U123", contract=contract_bad, position="NOT_AN_INT", avgCost=200)

    mock_client.get_positions.return_value = [pos_ok, pos_bad]

    mock_find_ok = MagicMock()
    mock_find_ok.first.return_value = None # OK is new
    # BAD position won't reach DB query for existing due to error earlier

    # No open positions in DB for closing logic part to keep it simple
    mock_get_all_open_db = MagicMock()
    mock_get_all_open_db.all.return_value = []

    # Only one successful call to .exec().first() for pos_ok
    # The error for pos_bad happens before the DB lookup for existing.
    session_mock.exec.side_effect = [
        mock_find_ok,
        mock_get_all_open_db
    ]

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=session_mock):
            result = await service.sync_portfolio_positions(ibkr_account_id_filter="U123")

    assert result["status"] == "success" # Overall sync might be 'success' but with errors
    assert result["new_items"] == 1      # OK position
    assert result["updated_items"] == 0
    assert result["processed_items"] == 1 # OK position processed
    assert result["errors"] == 1         # BAD position caused an error

    added_obj = session_mock.add.call_args[0][0]
    assert added_obj.symbol == "OK"
    session_mock.commit.assert_called_once() # Commit should still be called for successful parts


@pytest.mark.asyncio
async def test_sync_position_goes_to_zero_quantity_in_ibkr(sync_service_components, mock_session):
    service, mock_client, session_mock = sync_service_components

    db_pos_to_zero = PortfolioPosition(
        id=1, symbol="ZERO", ibkr_account_id="U123", ibkr_con_id=100,
        quantity=50, entry_price=200.0, status="OPEN", entry_date=date(2023,1,1)
    )

    mock_find_existing = MagicMock()
    mock_find_existing.first.return_value = db_pos_to_zero

    contract_zero = create_mock_ib_contract(symbol="ZERO", conId=100)
    # IBKR reports same position but with quantity 0
    ibkr_pos_zero = create_mock_ib_position(account="U123", contract=contract_zero, position=0, avgCost=200.0)
    mock_client.get_positions.return_value = [ibkr_pos_zero]

    mock_get_all_open_db = MagicMock()
    # For the closing logic, this position (db_pos_to_zero) is initially in the list of open positions.
    # However, the ibkr_active_positions_set will be empty for (100, "U123") because its quantity is 0.
    # So it should be identified for closure IF the update logic for quantity 0 didn't already close it.
    # The service's current logic: if pos.position == 0 and existing_position.status == "OPEN", it's marked CLOSED.
    # This happens during the update part.
    mock_get_all_open_db.all.return_value = [] # Assume it's handled in update, so not "closed again" by stale logic.
                                              # Or, if it was still [db_pos_to_zero], the active set check would handle it.

    session_mock.exec.side_effect = [mock_find_existing, mock_get_all_open_db]

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=session_mock):
            result = await service.sync_portfolio_positions(ibkr_account_id_filter="U123")

    assert result["status"] == "success"
    assert result["new_items"] == 0
    assert result["updated_items"] == 1 # Technically an update that leads to closure state
    assert result["closed_in_db"] == 0 # Not closed by the "stale DB" logic, but by quantity update.
                                      # The service's summary might need refinement if this is "closed" vs "updated".
                                      # Based on current service code, it's an update.

    assert db_pos_to_zero.status == "CLOSED"
    assert db_pos_to_zero.quantity == 0 # Ensure quantity is also updated.
    assert db_pos_to_zero.exit_date == date.today()
    session_mock.add.assert_called_with(db_pos_to_zero)
    session_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sync_disconnects_on_error(sync_service_components, mock_session):
    service, mock_client, _ = sync_service_components
    mock_client.get_positions.side_effect = Exception("IBKR API Error")

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=mock_session):
            result = await service.sync_portfolio_positions()

    assert result["status"] == "error"
    mock_client.disconnect.assert_awaited_once()

@pytest.mark.asyncio
async def test_sync_disconnects_on_success(sync_service_components, mock_session):
    service, mock_client, _ = sync_service_components
    mock_client.get_positions.return_value = []

    with patch('backend.ibkr_sync_service.IBKRClient', return_value=mock_client):
        with patch('backend.ibkr_sync_service.Session', return_value=mock_session):
            await service.sync_portfolio_positions()

    mock_client.disconnect.assert_awaited_once()

# Remaining TODOs from previous file are still relevant for further expansion.
