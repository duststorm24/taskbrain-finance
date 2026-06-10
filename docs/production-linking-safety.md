# Plaid Production Linking Safety

TaskBrain Finance can store Plaid production credentials before real institution linking is enabled. This makes it possible to finish UI and security work without accidentally connecting real accounts.

## Current Safe Default

Production linking is disabled unless both settings are true at the same time:

```text
PLAID_ENV=production
PLAID_ALLOW_PRODUCTION_LINKING=true
```

If `PLAID_ENV=production` but `PLAID_ALLOW_PRODUCTION_LINKING=false`, the backend rejects new Plaid Link token creation and public-token exchange requests.

## Recommended Enablement Order

1. Finish UI, AI analysis, graph tuning, and deletion/retention controls.
2. Run the local security check:

   ```bash
   ./.venv/bin/python finance/backend/scripts/local_security_check.py
   ```

3. Confirm the app is only reachable locally or through Tailscale/private networking.
4. Set `PLAID_ENV=production`.
5. Restart the backend and confirm the UI says production linking is locked.
6. Only when ready, set `PLAID_ALLOW_PRODUCTION_LINKING=true`.
7. Restart the backend again and connect real institutions from the UI.

## Disconnect And Delete

Each Plaid Item shown in the dashboard has a `Disconnect & delete` control. The backend attempts to revoke the Plaid Item through Plaid and then deletes associated local accounts, balances, transactions, recurring streams, snapshots, sync history, and generated AI summaries.

If the Plaid revocation call fails, local data is not deleted automatically. This avoids a confusing state where the app forgets an institution locally but Plaid access remains active.
