#!/bin/bash
cd /mnt/c/Users/rifra/.gemini/antigravity-ide/scratch/ai-second-brain || exit 1
exec python3 meeting-recorder/watcher.py --file \
  /mnt/c/Users/rifra/MeetingRecordings/2026-08-19_1612_monthly_meet_aGROWforests.wav
