# WhatsApp Connection Check

Every time a new conversation starts or you are first opened (especially after a server restart or long idle period), you MUST automatically check the WhatsApp Web connection status before proceeding with other tasks.

## How to check
1. Ensure the CDP server is running by executing: `wsl bash .agent/skills/browser-service/scripts/ensure_cdp.sh`
2. If it was not running or you need to verify the login state, you should take a screenshot or query the DOM via CDP to ensure WhatsApp is successfully logged in and not stuck on a QR code.
3. If it is stuck on a QR code, immediately notify the user and provide instructions on how to re-authenticate (e.g., by running the CDP server non-headless so they can scan).
