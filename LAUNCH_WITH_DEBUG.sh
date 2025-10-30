#!/bin/bash
# Launch teleop with debug logging captured to a file

LOGFILE="servo_debug_$(date +%Y%m%d_%H%M%S).log"

echo "Launching teleop with debug logging to: $LOGFILE"
echo "Press Ctrl+C to stop"

ros2 launch za6_moveit_config teleop_gamepad_sim.launch.py 2>&1 | tee "$LOGFILE"

