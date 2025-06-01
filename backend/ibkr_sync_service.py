import asyncio
from datetime import date, datetime # Added datetime
from sqlmodel import Session, select # Added select
from ibkr_client import IBKRClient # Assuming backend.ibkr_client path
from models import PortfolioPosition # Assuming backend.models path
# We'll need the database engine for session creation. This might need to be passed in
# or accessed via a global/singleton if that's the pattern in main.py.
# For now, let's assume it's passed to the service.
# from main import engine # This would be a circular import if service is used in main

class IBKRSyncService:
    def __init__(self, db_engine): # db_engine for creating sessions
        self.ibkr_client = IBKRClient() # Default connection params
        self.db_engine = db_engine

    async def sync_portfolio_positions(self, ibkr_account_id_filter: str = None):
        '''
        Synchronizes portfolio positions from IBKR to the local database.
        If ibkr_account_id_filter is provided, only positions from that account are synced.
        '''
        print(f"Starting IBKR portfolio sync. Account filter: {ibkr_account_id_filter}")
        if not await self.ibkr_client.connect():
            print("Failed to connect to IBKR. Aborting sync.")
            return {"status": "error", "message": "Failed to connect to IBKR"}

        synced_count = 0
        updated_count = 0
        new_count = 0
        error_count = 0
        positions_closed_in_db = 0 # Initialize here

        try:
            # Fetch portfolio items from IBKR
            # ib.portfolio() returns PortfolioItem objects
            # ibkr_portfolio_items = await self.ibkr_client.get_portfolio() # Not using this one
            # ib.positions() returns Position objects, which are often more detailed for multi-account.
            ibkr_positions = await self.ibkr_client.get_positions()

            if not ibkr_positions:
                print("No positions returned from IBKR.")
                # If no positions are returned, it means all positions for the filtered account (or all accounts if no filter)
                # should be considered closed if they exist in our DB.

            with Session(self.db_engine) as session:
                for pos in ibkr_positions:
                    # Apply account filter if provided
                    if ibkr_account_id_filter and pos.account != ibkr_account_id_filter:
                        continue

                    try:
                        existing_position = session.exec(
                            select(PortfolioPosition).where(
                                PortfolioPosition.ibkr_account_id == pos.account,
                                PortfolioPosition.ibkr_con_id == pos.contract.conId,
                                PortfolioPosition.symbol == pos.contract.symbol
                            )
                        ).first()

                        if existing_position:
                            # Update existing position
                            existing_position.quantity = int(pos.position)
                            existing_position.entry_price = pos.avgCost
                            existing_position.currency = pos.contract.currency
                            existing_position.exchange = pos.contract.exchange # Make sure this is the primary exchange or clearing exchange
                            existing_position.sec_type = pos.contract.secType

                            if pos.position == 0 and existing_position.status == "OPEN":
                                existing_position.status = "CLOSED"
                                existing_position.exit_date = date.today()
                            elif pos.position != 0 and existing_position.status == "CLOSED":
                                # If a position reappears or quantity becomes non-zero, reopen it.
                                existing_position.status = "OPEN"
                                existing_position.exit_date = None # Clear exit date

                            session.add(existing_position)
                            updated_count += 1
                        else:
                            if pos.position == 0: # Don't add new zero-quantity positions
                                continue

                            new_pos = PortfolioPosition(
                                symbol=pos.contract.symbol,
                                entry_date=date.today(),
                                entry_price=pos.avgCost,
                                quantity=int(pos.position),
                                status="OPEN",
                                ibkr_account_id=pos.account,
                                ibkr_con_id=pos.contract.conId,
                                sec_type=pos.contract.secType,
                                currency=pos.contract.currency,
                                exchange=pos.contract.exchange, # Make sure this is the primary exchange or clearing exchange
                                notes=f"Synced from IBKR on {date.today().isoformat()}"
                            )
                            session.add(new_pos)
                            new_count += 1

                        synced_count += 1
                    except Exception as e:
                        print(f"Error processing position {pos.contract.symbol} (ConID: {pos.contract.conId}) for account {pos.account}: {e}")
                        error_count += 1

                # --- Logic for positions in DB but not in IBKR (i.e., closed in IBKR) ---
                db_positions_query = select(PortfolioPosition).where(PortfolioPosition.status == "OPEN")
                if ibkr_account_id_filter:
                    db_positions_query = db_positions_query.where(PortfolioPosition.ibkr_account_id == ibkr_account_id_filter)
                else:
                    # If no specific account filter, we should only affect positions that have an ibkr_account_id
                    # to avoid closing manually entered positions that were never synced.
                    db_positions_query = db_positions_query.where(PortfolioPosition.ibkr_account_id != None)

                all_open_db_positions = session.exec(db_positions_query).all()

                ibkr_active_positions_set = set()
                for pos in ibkr_positions:
                    if ibkr_account_id_filter and pos.account != ibkr_account_id_filter:
                        continue
                    # A position is active if its quantity is not zero.
                    # The IBKR API might return positions with quantity 0 if they had activity during the day
                    # but were closed out. So, explicitly check for non-zero.
                    if pos.position != 0:
                         ibkr_active_positions_set.add((pos.contract.conId, pos.account))

                for db_pos in all_open_db_positions:
                    # Ensure it's an IBKR-managed position and has con_id and account_id
                    if db_pos.ibkr_con_id is not None and db_pos.ibkr_account_id is not None:
                        # If applying a filter, ensure we only close positions for that account
                        if ibkr_account_id_filter and db_pos.ibkr_account_id != ibkr_account_id_filter:
                            continue

                        if (db_pos.ibkr_con_id, db_pos.ibkr_account_id) not in ibkr_active_positions_set:
                            print(f"Position for {db_pos.symbol} (ConID: {db_pos.ibkr_con_id}, Acc: {db_pos.ibkr_account_id}) not found in active IBKR positions. Marking as CLOSED.")
                            db_pos.status = "CLOSED"
                            db_pos.exit_date = date.today()
                            db_pos.quantity = 0
                            session.add(db_pos)
                            positions_closed_in_db +=1

                if positions_closed_in_db > 0:
                    print(f"Marked {positions_closed_in_db} positions as CLOSED in DB.")

                session.commit()
                print(f"Sync complete. Processed: {synced_count}, New: {new_count}, Updated: {updated_count}, Closed in DB: {positions_closed_in_db}, Errors: {error_count}")

        except Exception as e:
            print(f"An error occurred during the sync process: {e}")
            # Rollback session on error? Session is commited before this block, maybe not necessary.
            # However, if error happens before commit, session context manager handles rollback.
            return {"status": "error", "message": str(e), "details": f"Processed: {synced_count}, New: {new_count}, Updated: {updated_count}, Closed: {positions_closed_in_db}, Errors: {error_count}"}
        finally:
            await self.ibkr_client.disconnect()
            print("Disconnected from IBKR after sync.")

        return {
            "status": "success",
            "message": "IBKR portfolio sync completed.",
            "processed_items": synced_count,
            "new_items": new_count,
            "updated_items": updated_count,
            "closed_in_db": positions_closed_in_db,
            "errors": error_count
        }

# Example of how this service might be used (for conceptual understanding)
async def example_run_sync(db_engine_obj):
    sync_service = IBKRSyncService(db_engine=db_engine_obj)
    # result = await sync_service.sync_portfolio_positions()
    # print(result)
    # result_specific_account = await sync_service.sync_portfolio_positions(ibkr_account_id_filter="U1234567")
    # print(result_specific_account)

if __name__ == "__main__":
    print("IBKRSyncService created. Example usage requires DB engine and IBKR connection.")
    print("Run from an endpoint in main.py that provides the DB engine.")
    # from sqlmodel import create_engine
    # DATABASE_URL = "postgresql://user:password@host:port/database"
    # engine = create_engine(DATABASE_URL)
    #
    # async def main_test():
    #    await example_run_sync(engine)
    #
    # if util.runningInNotebook(): # ib_insync util for notebook check
    #     util.patchAsyncio()
    #     asyncio.get_event_loop().run_until_complete(main_test())
    # else:
    #     asyncio.run(main_test())
