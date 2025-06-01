import asyncio
import os # Added import
from ib_insync import IB, util, Contract, Forex, Stock, Option, PortfolioItem, Position

class IBKRClient:
    def __init__(self, host=None, port=None, client_id=None):
        self.ib = IB()
        self.host = host or os.getenv('IBKR_HOST', '127.0.0.1')
        self.port = port if port is not None else int(os.getenv('IBKR_PORT', '7497'))
        self.client_id = client_id if client_id is not None else int(os.getenv('IBKR_CLIENT_ID', '1'))
        self.is_connected = False

    async def connect(self):
        if not self.ib.isConnected():
            try:
                await self.ib.connectAsync(self.host, self.port, self.client_id)
                self.is_connected = True
                print(f"Successfully connected to IBKR on {self.host}:{self.port}")
            except ConnectionRefusedError:
                print(f"Connection refused. Ensure TWS or IB Gateway is running and API connections are enabled on {self.host}:{self.port}.")
                self.is_connected = False
            except Exception as e:
                print(f"Error connecting to IBKR: {e}")
                self.is_connected = False
        return self.is_connected

    async def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()
            self.is_connected = False
            print("Disconnected from IBKR.")

    async def get_portfolio(self) -> list[PortfolioItem]:
        if not await self.connect():
            return []
        try:
            # Ensure event loop is running for ib_insync background tasks
            if not asyncio.get_event_loop().is_running():
                 util.startLoop() # Starts a new event loop if none is running

            portfolio = await self.ib.portfolioAsync()
            return list(portfolio)
        except Exception as e:
            print(f"Error fetching portfolio: {e}")
            return []

    async def get_positions(self) -> list[Position]:
        if not await self.connect():
            return []
        try:
            if not asyncio.get_event_loop().is_running():
                 util.startLoop()

            positions = await self.ib.positionsAsync() # Fetches all positions for all accounts
            return list(positions)
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []

    async def get_account_summary(self, account="all", tags="NetLiquidation,TotalCashValue,AvailableFunds"):
        if not await self.connect():
            return None
        try:
            if not asyncio.get_event_loop().is_running():
                 util.startLoop()
            # For accountSummary, it's better to use run() as it's not directly an async method in the same way
            # and needs proper handling if run from an existing loop.
            # However, ib_insync methods are generally awaitable when used with connectAsync.
            # Let's try to make it directly awaitable or wrap it.
            # account_summary = await self.ib.accountSummaryAsync(account, tags) # This method doesn't exist
            # Fallback to synchronous call wrapped if necessary or use reqAccountSummary

            # Request account summary (this is a subscription, so we need to handle it)
            # For simplicity in a direct client, fetching current values might be preferred.
            # The `accountValues` method is often more straightforward for a snapshot.
            account_values = self.ib.accountValues(account) # This is synchronous
            summary = {av.tag: av.value for av in account_values if av.tag in tags.split(',')}

            # If you need truly async, you'd subscribe and handle updates.
            # For a one-time fetch, this synchronous part is often acceptable within an async method
            # if the underlying library manages its own event loop interactions correctly.
            # Or, more correctly, use ib.reqAccountSummary() and handle the updates.
            # For now, let's assume the synchronous `accountValues` is sufficient for a snapshot.
            # A more robust solution might involve `ib.reqAccountSummary()` and waiting for `accountSummary` events.

            return summary # This part needs refinement for true async operation or snapshot.
                           # The current ib_insync version might handle this better with `ib.accountSummary()` directly.
                           # Let's assume a direct call for now and refine if test reveals issues.
        except Exception as e:
            print(f"Error fetching account summary: {e}")
            return None

# Example Usage (for testing purposes, can be removed later)
async def main():
    client = IBKRClient()
    if await client.connect():
        print("Connection successful.")

        portfolio_items = await client.get_portfolio()
        if portfolio_items:
            print("\nPortfolio:")
            for item in portfolio_items:
                print(f"  Symbol: {item.contract.symbol}, SecType: {item.contract.secType}, Position: {item.position}, Market Price: {item.marketPrice}, Market Value: {item.marketValue}, Average Cost: {item.averageCost}")
        else:
            print("\nNo portfolio items found or error fetching.")

        positions = await client.get_positions()
        if positions:
            print("\nPositions (detailed):")
            for pos in positions:
                 print(f"  Account: {pos.account}, Symbol: {pos.contract.symbol}, SecType: {pos.contract.secType}, Position: {pos.position}, Avg Cost: {pos.avgCost}")
        else:
            print("\nNo positions found or error fetching.")

        # account_summary = await client.get_account_summary()
        # if account_summary:
        #     print("\nAccount Summary:")
        #     for tag, value in account_summary.items():
        #         print(f"  {tag}: {value}")
        # else:
        #     print("\nCould not fetch account summary.")

        await client.disconnect()

if __name__ == "__main__":
    # util.patchAsyncio() # Apply if running in environments like Jupyter notebooks
    # asyncio.run(main()) # This is for Python 3.7+
    # For older versions or specific setups, you might need:
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Manual interruption.")
    finally:
        # Ensure disconnection if loop is interrupted
        # This part is tricky as client might not be in scope or initialized
        # Consider atexit or a more robust cleanup mechanism if this script were to run standalone often
        pass
