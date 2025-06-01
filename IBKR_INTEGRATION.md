# Interactive Brokers (IBKR) Portfolio Synchronization Integration

This document provides instructions on how to set up and use the Interactive Brokers (IBKR) portfolio synchronization feature. This allows you to import and update your IBKR portfolio positions within this application.

## 1. IBKR Setup (Trader Workstation or IB Gateway)

This integration requires a running instance of either Interactive Brokers Trader Workstation (TWS) or IB Gateway. The application connects to this instance to access your portfolio data.

**Key Configuration Steps in TWS/Gateway:**

1.  **Enable API Access:**
    *   In TWS: Go to **File > Global Configuration > API > Settings**.
    *   In IB Gateway: Configuration is typically done via a settings file or initial setup screen.
    *   Ensure "**Enable ActiveX and Socket Clients**" (or a similarly named option) is **checked**. This is the master switch for API connectivity.

2.  **Configure Trusted IP Addresses:**
    *   For security, it's highly recommended to specify which IP addresses can connect to the API.
    *   Under API Settings, look for a section related to "Trusted IPs".
    *   **If running TWS/Gateway on the same machine as this application (e.g., for local development):** Add `127.0.0.1` to the list of trusted IPs.
    *   **If running TWS/Gateway on a dedicated server and this application on another server:** Add the static IP address of the server where this application is hosted. If the application server has a dynamic IP, this method is less secure; consider network-level restrictions or running both on the same secured machine/network.
    *   **Caution:** Leaving "Allow connections from anywhere" or not specifying trusted IPs can be a security risk, especially if the machine running TWS/Gateway is accessible from the internet.

3.  **Note the Port Number:**
    *   The API socket port number is crucial for the application to connect.
    *   Default for TWS (production account): `7496`
    *   Default for TWS (paper trading account): `7497`
    *   Default for IB Gateway (production account): `4001`
    *   Default for IB Gateway (paper trading account): `4002`
    *   Verify this port in your TWS/Gateway API settings.

4.  **Ensure TWS/Gateway is Running and Logged In:**
    *   TWS or IB Gateway **must be running and logged into your Interactive Brokers account** for the synchronization to work.
    *   The API connection is made through this running instance. This application does **not** directly handle your IBKR username and password. Authentication to IBKR is managed by your TWS/Gateway login.
    *   **For Server Deployments:** If you intend to run this on a server for automated syncs, you'll need to ensure IB Gateway (preferred over TWS for servers) is configured to run persistently (e.g., as a service, or using tools like `systemd` on Linux or Task Scheduler on Windows) and ideally set up for automatic login if your security policy allows. Refer to IBKR documentation for headless Gateway operation.

**Important Note on API Keys:**
This integration uses the `ib_insync` library, which connects to the running TWS/Gateway instance. It does **not** use separate, standalone API keys that you might generate on the IBKR website for other services. The "authentication" is your active login session within TWS/Gateway.

## 2. Application Configuration (Environment Variables)

The application needs to know how to connect to your running TWS/Gateway instance. Configure the following environment variables in your application's environment (e.g., in a `.env` file, or your deployment platform's configuration):

*   **`IBKR_HOST`**:
    *   Description: The hostname or IP address where your TWS or IB Gateway is running.
    *   Example (Gateway on the same machine): `IBKR_HOST=127.0.0.1`
    *   Example (Gateway on a different server): `IBKR_HOST=192.168.1.100` (replace with actual IP)

*   **`IBKR_PORT`**:
    *   Description: The port number your TWS or IB Gateway is listening on for API connections.
    *   Example (TWS paper account): `IBKR_PORT=7497`
    *   Example (IB Gateway live account): `IBKR_PORT=4001`

*   **`IBKR_CLIENT_ID`**:
    *   Description: A unique client ID for this API connection. Each client connecting to TWS/Gateway should use a unique ID.
    *   Default used by the application if not set: `1`
    *   Example: `IBKR_CLIENT_ID=1` (or any integer, e.g., `101`, `202`)
    *   If you run multiple instances of this application or other API tools connecting to the *same* TWS/Gateway, ensure each has a distinct client ID.

## 3. How to Use the Synchronization Feature

Once TWS/Gateway is running and the application is configured with the correct environment variables:

1.  **Trigger Synchronization:**
    *   Make a **POST** request to the following API endpoint:
        `/portfolio/sync/ibkr`
    *   This will initiate the process of fetching your portfolio positions from IBKR and updating them in the application's database.

2.  **Optional: Sync a Specific Account:**
    *   If you have multiple IBKR accounts linked under your user and want to sync only a specific one, you can use the `ibkr_account_id` query parameter:
        `POST /portfolio/sync/ibkr?ibkr_account_id=U1234567`
        (Replace `U1234567` with your actual IBKR account ID).
    *   If this parameter is omitted, the service will attempt to sync positions from all accounts accessible through the TWS/Gateway connection.

3.  **Response:**
    *   A successful sync will return a JSON response with a `status: "success"` and details about the sync operation (items processed, new, updated, errors, etc.).
    *   If there's an error (e.g., cannot connect to TWS/Gateway), it will return an appropriate HTTP error code (like 500) with an error message.

## 4. Troubleshooting Common Issues

*   **Connection Refused / Cannot Connect:**
    *   Verify TWS/Gateway is running and logged in.
    *   Double-check `IBKR_HOST` and `IBKR_PORT` environment variables match your TWS/Gateway API settings.
    *   Ensure "Enable ActiveX and Socket Clients" is enabled in TWS/Gateway.
    *   Check your Trusted IP settings in TWS/Gateway. If running the app on a different machine, its IP must be listed.
    *   Test basic network connectivity (e.g., `ping IBKR_HOST`, `telnet IBKR_HOST IBKR_PORT` from the application server if possible).
    *   Check firewalls on both the machine running TWS/Gateway and the machine running the application.

*   **No Positions Synced:**
    *   Verify you have positions in the IBKR account you are trying to sync.
    *   If using an account filter, ensure the `ibkr_account_id` is correct.
    *   Check TWS/Gateway logs for any API-related error messages.
    *   Check application logs for more detailed error information.

*   **"Client ID in use" Error (or similar):**
    *   Ensure `IBKR_CLIENT_ID` is unique if multiple applications are connecting to the same TWS/Gateway instance. Try changing it.

*   **Old/Stale Data:**
    *   Ensure TWS/Gateway has an active market data subscription if you rely on real-time price updates (though this sync focuses on positions, market data status can affect API behavior). This application fetches positions; market prices shown elsewhere might come from a different source like Polygon.

*   **Application Logs:**
    *   The application backend will log information during the sync process, including connection attempts, errors, and summary statistics. Check these logs for details if you encounter issues.
```
