#!/bin/bash

# Remove temporary analysis and debugging files
rm -f HARDCODE_LOCATIONS.md
rm -f PANDA_ARM_HARDCODE_ANALYSIS.md
rm -f START_SERVO.md
rm -f FIX_SERVO.md
rm -f CHECK_SERVO_STATUS.sh
rm -f DIAGNOSE_GAMEPAD.sh
rm -f INTEGRATION_SUMMARY.md
rm -f MOVEIT2_MODIFICATIONS.md
rm -f CHAT_CONTEXT_SUMMARY.md
rm -f TEST_SERVO_COMMANDS.md
rm -f BUILD_COMMAND.txt

# Remove temporary build scripts (keep the good ones)
rm -f BUILD_MOVEIT_CORRECT.sh
rm -f BUILD_MOVEIT_FINAL.sh
rm -f BUILD_MOVEIT_SERVO_DIRECT.sh
rm -f BUILD_MOVEIT_SERVO.sh
rm -f BUILD_MOVEIT_TMP.sh
rm -f BUILD_ZA6_WORKSPACE.sh
rm -f TEST_MODIFIED_SERVO.sh
rm -f test_servo.sh

# Remove stray files created during testing
rm -f servo_debug_*.log
rm -f grasp_link
rm -f manipulator
rm -f tool0
rm -f world

# Remove duplicate config (keep servo_params.yaml, not servo_params_complete.yaml)
rm -f za6_moveit_config/config/servo_params_complete.yaml

echo "Cleaned up temporary files"
echo ""
echo "Files kept for future work:"
echo "  - MOVEIT_SERVO_INTEGRATION.md (documentation)"
echo "  - DEBUG_SERVO.md (debugging guide)"
echo "  - WORK_SUMMARY.md (work summary)"
echo "  - REBUILD_SERVO.sh (build script)"
echo "  - LAUNCH_WITH_DEBUG.sh (debug launch)"
echo ""

