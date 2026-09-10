#!/bin/bash
# Consume stdin to satisfy hook contract
cat > /dev/null

# Only run once per WSL boot / temp clear
if [ ! -f /tmp/agy_startup_done ]; then
    touch /tmp/agy_startup_done
    
    # 1. Ensure watcher.py is running as daemon (Auto MOM generation)
    if ! pgrep -f "meeting-recorder/watcher.py" > /dev/null; then
        nohup python3 meeting-recorder/watcher.py > /tmp/watcher_daemon.log 2>&1 &
    fi
    
    # 2. Ensure WhatsApp CDP browser service is running
    bash .agent/skills/browser-service/scripts/ensure_cdp.sh > /dev/null 2>&1
fi

# Fulfill the JSON output contract for PreInvocation
echo '{"injectSteps": []}'
