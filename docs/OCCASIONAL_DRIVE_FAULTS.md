# Occasional Drive Faults During MoveIt Execution

## Problem Statement

During MoveIt trajectory execution (both standard RViz "Plan and Execute" and MTC tasks), the robot drives occasionally fault, causing motion to stop. This document summarizes possible root causes and diagnostic approaches.

## Observed Behavior

- **Scope**: Affects both standard MoveIt execution (RViz "Plan and Execute") and MTC pipeline execution
- **Symptom**: Drive faults during trajectory execution, causing motion to abort
- **Frequency**: Intermittent, not every execution (can occur after multiple successful executions)
- **Two distinct root causes identified**:
  1. **Untimed trajectories** (captured/replayed MTC solutions) - causes immediate QUICK STOP
  2. **Control mode loss** (standard MoveIt execution) - causes `MODE_CSP` → `MODE_NA` transition during execution

## Actual Root Causes (Based on Launch Logs)

### **1. Untimed Trajectories** 🔴 (Confirmed - Primary Issue)

**Analysis of `mtc_test-doorhello.yaml` and `launch_20251117_195237.log`:**

The YAML file contains trajectories with **ALL waypoints having `time_from_start: {sec: 0, nanosec: 0}`**. This causes:

1. **Controller accepts trajectory** but reports "Goal reached, success!" suspiciously fast (~20ms)
2. **Drives enter QUICK STOP ACTIVE** state immediately after (status_word `0x0217`)
3. **Some drives fault** with error code `0x0B000B00` (position/trajectory following error)
4. **Drives enter FAULT REACTION ACTIVE** (status_word `0x021F`)

**Root Cause**: The captured MTC solution was not time-parameterized before being saved to YAML. When replayed via `ros2 action send_goal`, the controller receives untimed trajectories that it cannot properly execute.

**Solution**: Time-parameterize the solution before saving to YAML, or ensure the MTC execution capability applies time parameterization (which it should via `IterativeParabolicTimeParameterization`).

**Error Code `0x0B000B00`**: Different from `0x0E080E08`, likely indicates position following error or trajectory following violation, consistent with untimed trajectory execution.

### **2. Drive Control Mode Loss (During Execution AND Idle)** 🔴 (Confirmed - Secondary Issue)

**Critical Finding: Faults occur during IDLE periods, not just during trajectory execution!**

**Analysis of multiple log sequences:**

1. **During trajectory execution** (`launch_20251117_195237.log` - RViz "Plan and Execute" sequence):
   - Multiple successful movements executed before fault
   - Drive 0 faults first, then all drives lose control mode

2. **During inactivity** (observation 1 - 2025-11-17 20:15:17):
   - Drives were in `OPERATION ENABLED` state (status_word `0x1637` with `TARGET_REACHED` flag)
   - **No trajectory execution was happening** - robot was idle
   - After ~10 seconds of inactivity, drives suddenly lost control mode:
     - Drives 0, 3: `NOT READY TO SWITCH ON` (status_word `0x0000`)
     - Drives 1, 2, 4, 5: `QUICK STOP ACTIVE` (status_word `0x0617`)
   - Control mode loss: `control_mode MODE_NA != MODE_CSP`
   - Error code `0x0E080E08` appeared after fault state entered

3. **During inactivity** (observation 2 - 2025-11-17 20:19:45, ~4 minutes after previous fault):
   - **No trajectory execution was happening** - robot was idle
   - All 6 drives simultaneously transitioned to `NOT READY TO SWITCH ON` (status_word `0x0000`)
   - Control mode loss: `control_mode MODE_NA != MODE_CSP`
   - Error code `0x0E080E08` appeared on all drives
   - All drives went "non-operational"
   - Drives recovered after error code cleared

**This proves the issue is NOT trajectory-related** - it's a system-level EtherCAT/HAL communication or control loop stability problem.

**Recurring Pattern**: Faults occur during idle periods with no trajectory execution, confirming this is a communication/stability issue, not a motion control issue.

**Fault Pattern:**
1. **Multiple successful executions**: 7+ "Plan and Execute" movements completed successfully (DOOR_FACING_NEUTRAL ↔ DOOR_HELLO)
2. **During trajectory execution**: Drive 0 faults first with error code `0x0E080E08`
3. **Cascade failure**: All other drives (1-5) immediately lose control mode:
   - `control_mode MODE_NA != MODE_CSP`
   - `state NOT READY TO SWITCH ON != OPERATION ENABLED`
   - Status word changes from `0x1237` (OPERATION ENABLED) to `0x0000` (NOT READY TO SWITCH ON)
4. **Controller reports success**: `joint_trajectory_controller` still reports "Goal reached, success!" despite drives faulting
5. **Error code**: `0x0E080E08` (Unknown error code, consistent across all 6 drives)
6. **Post-fault recovery**: After fault clears, additional drives (4, 5, 0, 2) fault again with same error code

**Key Findings:**
- The drives lose their control mode (`MODE_CSP` → `MODE_NA`) **both during execution AND during idle periods**
- This is **NOT** a trajectory velocity/acceleration issue (faults occur even when no trajectory is executing)
- This is **NOT** specific to MTC or untimed trajectories (occurs with standard MoveIt execution and during idle)
- The fault appears to be **intermittent** and **system-wide** (all drives affected simultaneously or in rapid succession)
- **Most likely cause**: EtherCAT communication loss or HAL control loop interruption, not trajectory execution

**Additional Observations:**
- Controller still reports "Goal reached, success!" even though drives faulted mid-execution
- MoveIt reports "Solution was found and executed" - execution monitoring doesn't detect drive faults
- Second fault occurs ~12 seconds after first fault clears (same error code)
- All 6 drives fault simultaneously, suggesting a system-wide issue (EtherCAT bus, HAL, or control mode switching)

**Possible Causes of Control Mode Loss (Ranked by Likelihood):**

1. **EtherCAT watchdog timeout** - **MOST LIKELY**: Drives have internal watchdogs that trigger if EtherCAT communication is lost for too long. During idle periods, if the EtherCAT master stops sending cyclic data or misses cycles, drives will timeout and lose control mode. This explains why faults occur during idle.

2. **EtherCAT communication loss** - Network jitter, cable issues, or EtherCAT cycle misses. The fact that faults occur during idle suggests the EtherCAT master may stop sending cyclic data when no motion is commanded, causing drives to timeout.

3. **HAL control loop interruption** - Real-time loop jitter or missed deadlines could cause EtherCAT cycle misses, even during idle periods.

4. **EtherCAT master timing issues** - Cycle time violations or synchronization loss. The master may have different behavior during idle vs. active periods.

5. **System resource exhaustion** - CPU/memory pressure causing EtherCAT communication delays, even during idle (background processes, garbage collection, etc.).

6. **Control mode switching logic** - Unexpected mode transitions (less likely given idle fault pattern).

7. **Drive configuration instability** - CiA 402 parameters not properly maintained (less likely given idle fault pattern).

## Other Potential Root Causes (For Reference)

### 1. **Aggressive Trajectory Timing** (Less Likely - Not Observed in Logs)

Even with conservative scaling factors, trajectories may exceed hardware limits if:
- Base joint limits in `joint_limits.yaml` are too high relative to actual HAL/drive hardware limits
- Trajectory time parameterization (`IterativeParabolicTimeParameterization`) fails or isn't applied consistently
- Multiple scaling layers conflict or aren't properly cascaded

**Current Configuration:**
- `joint_limits.yaml`: `default_velocity_scaling_factor: 0.1`, `default_acceleration_scaling_factor: 0.1`
- MTC execution (`execute_task_solution_capability.cpp`): `max_velocity_scaling = 0.05`, `max_acceleration_scaling = 0.08` (only for MTC paths)
- Base limits: `max_velocity: 2.0-6.2 rad/s`, `max_acceleration: 6.0-20.0 rad/s²`

**Issue**: Non-MTC trajectories (standard RViz "Plan and Execute") only use `joint_limits.yaml` defaults, which may still exceed HAL drive parameters.

### 2. **Trajectory Time Parameterization Failures**

MoveIt uses `IterativeParabolicTimeParameterization` to smooth trajectories and apply velocity/acceleration limits. If this fails silently:
- Trajectories may retain aggressive timestamps from the planner
- Velocity/acceleration limits may not be enforced

**Current Behavior**: The MTC execution capability logs a warning but continues if time parameterization fails (see `execute_task_solution_capability.cpp:190`).

### 3. **Hardware/HAL Drive Limits Lower Than Configured**

The actual CiA 402 drive limits in the HAL configuration may be lower than the `joint_limits.yaml` values, even after scaling:
- If HAL limits are `1.5 rad/s` but MoveIt sends `2.0 rad/s * 0.1 = 0.2 rad/s`, this should be safe
- However, if HAL limits are `0.15 rad/s` or there's unexpected dynamics, even scaled trajectories may fault

### 4. **RViz Scaling Sliders Overridden**

RViz Motion Planning panel has `velocity_scaling_factor` and `acceleration_scaling_factor` sliders (default: `0.1`). If these are set higher:
- Execution will be more aggressive than configured
- May exceed hardware limits even if `joint_limits.yaml` is conservative

### 5. **Multiple Scaling Layers Conflict**

Velocity/acceleration scaling is applied in multiple places:
- `joint_limits.yaml` → MoveIt planning/execution
- MTC execution capability → only for MTC tasks
- RViz UI sliders → runtime override
- Trajectory time parameterization → applies limits but may fail

If these aren't properly cascaded or conflict, trajectories may not respect hardware limits.

### 6. **Real-Time Control Loop Delays**

On resource-constrained hardware (like the ZA6 controller), real-time delays may cause:
- Trajectory waypoints to be executed late
- Jerky motion that triggers drive fault detection
- Control loop jitter exceeding drive tolerance

### 7. **Missing Trajectory Execution Timeout Configuration**

MoveIt may not have proper execution monitoring/timeout configuration, allowing trajectories to run longer than expected and accumulate errors.

## Configuration Files Involved

### Primary Configuration

- **`za6_moveit_config/config/joint_limits.yaml`**: Base joint limits and default scaling factors
  - `default_velocity_scaling_factor: 0.1`
  - `default_acceleration_scaling_factor: 0.1`
  - Per-joint `max_velocity` and `max_acceleration` values

- **`za6_moveit_config/config/ros2_controllers.yaml`**: Joint trajectory controller configuration
  - No explicit velocity/acceleration limits (uses MoveIt's limits)

- **`moveit_task_constructor/capabilities/src/execute_task_solution_capability.cpp`**: MTC execution capability
  - Applies `IterativeParabolicTimeParameterization` with `0.05/0.08` scaling
  - Only applies to MTC tasks

### RViz Configuration

- **Motion Planning Panel**: `velocity_scaling_factor` and `acceleration_scaling_factor` sliders
  - Default: `0.1` (read from `robot_description_planning.default_velocity_scaling_factor`)
  - Can be overridden at runtime

## Diagnostic Approach: Isolating Control Mode Loss

### Step 1: **Check for Untimed Trajectories** 🔍 (Start Here - Most Common Issue)

**If using captured/replayed MTC solutions:**

Check the YAML file for untimed trajectories:
```bash
# Check if all time_from_start values are zero
grep -A 5 "time_from_start:" <solution.yaml> | grep -E "sec: 0|nanosec: 0"
```

**Symptoms:**
- All waypoints have `time_from_start: {sec: 0, nanosec: 0}`
- Controller reports "Goal reached, success!" very quickly (< 100ms)
- Drives enter QUICK STOP ACTIVE immediately after trajectory starts
- Error code `0x0B000B00` (position/trajectory following error)

**Solution:**
- Time-parameterize the solution before saving to YAML
- Or ensure `IterativeParabolicTimeParameterization` is applied during execution
- See `MTC_EXPERIMENTS.md` for time parameterization implementation

### Step 2: **Decode Error Code `0x0E080E08` or `0x0B000B00`** 🔍

The error code provides the most direct clue about the fault cause:

```bash
# Check IS620N servo documentation or error code database
# Error code format: 0x0E080E08
# - Lower 16 bits (0x0E08) may indicate specific fault type
# - Upper 16 bits (0x0E08) may be repeated or indicate severity
```

**Common IS620N Error Codes:**
- Position following error
- Overcurrent/overload
- Communication timeout
- Encoder fault
- Control mode mismatch

**Action**: Look up `0x0E08` in IS620N servo documentation to identify the specific fault trigger.

### Step 3: **Monitor Control Mode Transitions During Idle** ⚠️ (HIGH PRIORITY)

**Since faults occur during idle periods, monitor for control mode loss when robot is not moving:**

```bash
# Monitor drive state during idle periods
ros2 topic echo /hal_io/drive_state \
  --qos-profile system_default | \
  grep -E "control_mode|MODE_CSP|MODE_NA|status_word|OPERATION ENABLED|QUICK STOP|NOT READY"
```

**What to look for:**
- Control mode transitions from `MODE_CSP` to `MODE_NA` during idle
- Status word changes from `0x1637` (OPERATION ENABLED) to `0x0000` (NOT READY) or `0x0617` (QUICK STOP)
- Timing of mode loss (does it correlate with system events, time since last motion, etc.)
- Whether all drives lose mode simultaneously or sequentially

**This is the most direct way to isolate the root cause** since it eliminates trajectory execution as a variable.

### Step 4: **Monitor Control Mode Transitions During Execution** ⚠️

Create a log of control mode changes during execution to identify when/how mode is lost:

**Option A: Monitor HAL Topics (If Available)**
```bash
# Monitor drive state topic for control mode changes
ros2 topic echo /hal_io/drive_state --qos-profile system_default | \
  grep -E "control_mode|MODE_CSP|MODE_NA"

# Or monitor all HAL status topics
ros2 topic list | grep hal
ros2 topic echo <hal_control_mode_topic> --qos-profile system_default
```

**Option B: Check HAL Logs Directly**
```bash
# Look for control mode transitions in HAL/hw_device_mgr logs
# Search for: "MODE_CSP", "MODE_NA", "control_mode"
grep -i "control_mode\|MODE_" <hal_log_file>
```

**What to look for:**
- Exact timestamp when control mode changes from `MODE_CSP` to `MODE_NA`
- Whether mode loss happens before or after the error code appears
- If mode loss is gradual (one drive at a time) or instantaneous (all drives)

### Step 5: **Check EtherCAT Communication Stability During Idle** (HIGHEST PRIORITY)

**Since faults occur during idle periods, this is the highest priority diagnostic step.**

All 6 drives faulting simultaneously during idle strongly suggests an EtherCAT bus-level issue:

**A. Monitor EtherCAT Cycle Time During Idle**

**CRITICAL**: Monitor cycle time behavior when robot is idle vs. during motion:

```bash
# Check EtherCAT master cycle time statistics (if accessible via HAL)
# Look for:
# - Cycle time violations (missed cycles) - ESPECIALLY during idle
# - Jitter (variance in cycle times) - does it increase during idle?
# - Communication loss indicators
# - Does the master continue sending cyclic data during idle?

# Example: Check HAL component for EtherCAT stats
# (Specific commands depend on HAL tooling)

# Key question: Does the EtherCAT master continue cyclic communication during idle,
# or does it stop/slow down, causing drive watchdogs to timeout?
```

**B. Check EtherCAT Cable/Termination**

Physical issues can cause intermittent communication loss:
```bash
# Visually inspect:
# - EtherCAT cable connections (secure, no damage)
# - Termination resistors (present at both ends of chain)
# - Cable routing (away from power cables, no kinks)

# If accessible, check EtherCAT master diagnostics:
# - Lost frame count
# - Retry count
# - Communication error rate
```

**C. Monitor EtherCAT Status Words During Idle**

The `status_word` field in the logs shows drive communication status:
```bash
# Extract status_word values before/during fault:
# Before fault (idle): 0x1637 (OPERATION ENABLED with TARGET_REACHED)
# During fault: 0x0000 (NOT READY TO SWITCH ON) or 0x0617 (QUICK STOP ACTIVE)

# Check if REMOTE flag is maintained (indicates EtherCAT communication)
# If REMOTE flag drops, EtherCAT communication was lost
# In observed faults, REMOTE flag is maintained in some drives (0x0617) but not others (0x0000)
# This suggests partial communication loss or inconsistent EtherCAT master behavior
```

**Symptoms of EtherCAT Issues:**
- All drives fault within same cycle/ms (bus-wide failure)
- Faults occur during idle periods (suggests watchdog timeout or cyclic data loss)
- `REMOTE` flag may or may not drop (partial communication loss possible)
- Some drives show `QUICK STOP ACTIVE` (0x0617) while others show `NOT READY TO SWITCH ON` (0x0000)
- Increasing cycle time jitter before fault
- Correlation with system load (CPU spikes, disk I/O)
- EtherCAT master may stop/slow cyclic communication during idle

### Step 6: **Check HAL Control Loop Stability**

HAL real-time control loop interruptions can cause control mode loss:

**A. Check Real-Time Kernel Performance**

```bash
# If running RT kernel, check RT loop jitter:
# (Specific tools depend on RT kernel - PREEMPT_RT, Xenomai, etc.)

# Example with rt-tests:
sudo cyclictest -p 99 -t <num_threads> -i 1000 -l 10000

# Look for:
# - Max latency spikes (should be < 100µs for EtherCAT)
# - Missed deadlines
# - Context switch delays
```

**B. Check HAL Component CPU Usage**

```bash
# Monitor HAL processes during execution:
top -p $(pgrep hal_mgr) -p $(pgrep hw_device_mgr) -p $(pgrep rtapi_app)

# Or use htop with thread view:
htop -H

# Look for:
# - CPU saturation (> 95% on single core)
# - Thread starvation
# - Process priority changes
```

**C. Check for Interrupts or Other RT Tasks**

```bash
# Check if other RT tasks are competing:
ps -eo pid,cmd,rtprio | grep -E "RT|-rt|realtime"

# Check interrupt statistics:
cat /proc/interrupts | grep -i "eth\|ethercat\|pcie"

# Look for:
# - High interrupt counts
# - Shared interrupt lines (IRQ conflicts)
```

**Symptoms of RT Loop Issues:**
- Control mode loss correlates with CPU spikes
- Increased latency before fault (latency grows over time)
- Other RT tasks competing for CPU time
- System load correlates with fault frequency

### Step 7: **Check Control Mode Switching Logic**

Verify that control mode switching logic isn't interfering during execution:

**A. Review HAL Configuration**

```bash
# Check HAL files for control mode switching logic:
# - Look for state machine transitions
# - Check for periodic mode checks/switches
# - Verify no mode switching during OPERATION ENABLED state

# Example locations:
# - hal_device_config.yaml
# - HAL component Python files (hal_plumber)
# - hw_device_mgr configuration
```

**B. Check for State Machine Interference**

```bash
# Monitor drive state machine transitions:
# Look for unexpected state transitions during OPERATION ENABLED

# In logs, search for:
# - State transition messages
# - Control mode change messages
# - "Goal not reached" messages that might trigger mode switches
```

**Symptoms of Mode Switching Issues:**
- Control mode changes before EtherCAT communication loss
- Mode switching logic triggered by other events (timeouts, state checks)
- Pattern: Mode change → EtherCAT error → Fault

### Step 8: **Check Drive Configuration Stability**

CiA 402 parameters might not be properly maintained:

**A. Monitor CiA 402 Parameters**

```bash
# Check if control mode parameter (0x6060) is being changed:
# (Requires EtherCAT diagnostic tools or HAL access)

# Look for:
# - Mode parameter writes during execution
# - Mode parameter reads returning unexpected values
# - Parameter initialization issues
```

**B. Check Drive Initialization**

```bash
# Verify drives maintain configuration after enabling:
# - Control mode (0x6060) should remain 8 (CSP) during execution
# - No SDO writes during cyclic operation
# - PDO mappings are stable
```

**Symptoms of Configuration Issues:**
- Control mode parameter changes during execution
- Drives re-initialize mid-execution
- Configuration not persistent across state transitions

### Step 9: **Correlate with System Events**

Check for external factors that might trigger faults:

**A. System Load Correlation**

```bash
# Monitor system load during execution:
iostat -x 1
vmstat 1
sar -u 1

# Look for:
# - Disk I/O spikes coinciding with faults
# - Memory pressure
# - CPU saturation from non-RT tasks
```

**B. Network Activity**

```bash
# Check for network traffic spikes:
iftop -i <eth_interface>
# Or:
tcpdump -i <eth_interface> -n

# EtherCAT uses dedicated network interface, but heavy traffic on
# other interfaces can affect system performance
```

**C. Docker/Container Resource Limits**

```bash
# If running in Docker, check container resource usage:
docker stats ros2-devel

# Look for:
# - CPU throttling
# - Memory pressure
# - I/O throttling
```

### Step 10: **Create Diagnostic Test Sequence**

Run a controlled test to reproduce and isolate the issue:

**A. Launch with Verbose HAL Debugging**

Enable verbose HAL debugging and capture all launch output to a file:

```bash
# Option 1: Redirect all output to a file (no terminal display)
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml \
  gamepad_config:=gamepad_config.yaml \
  db:=true \
  hal_debug_level:=5 \
  > /tmp/launch_$(date +%Y%m%d_%H%M%S).log 2>&1

# Option 2: Use tee to both see output AND save to file
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml \
  gamepad_config:=gamepad_config.yaml \
  db:=true \
  hal_debug_level:=5 \
  2>&1 | tee /tmp/launch_$(date +%Y%m%d_%H%M%S).log
```

**Important Notes:**
- `hal_debug_level:=5` enables verbose hardware debugging (HAL, EtherCAT, drive state transitions)
- Use `tee` (Option 2) if you want to see output in real-time while also saving it
- Use pure redirection (Option 1) if you want to minimize terminal output
- The `2>&1` redirects stderr to stdout so both are captured
- Use a timestamped filename to avoid overwriting previous logs

**B. Start Additional Monitoring in Separate Terminals**

```bash
# Terminal 1: Drive state topic
ros2 topic echo /hal_io/drive_state \
  --qos-profile system_default \
  > /tmp/drive_state_$(date +%Y%m%d_%H%M%S).log

# Terminal 2: System load monitoring
vmstat 1 > /tmp/system_load_$(date +%Y%m%d_%H%M%S).log

# Terminal 3: HAL-specific topic monitoring (if available)
ros2 topic list | grep hal
ros2 topic echo <hal_control_mode_topic> \
  --qos-profile system_default \
  > /tmp/hal_control_mode_$(date +%Y%m%d_%H%M%S).log

# Terminal 4: EtherCAT status (if accessible)
# Check for EtherCAT diagnostic topics or HAL components
```

**C. Execute Long Trajectory**

```bash
# From RViz or another terminal:
# - Execute a long trajectory (aim for ~40+ seconds to exceed typical fault time)
# - Or use MTC pipeline experiment with a long sequence
# - Wait for fault to occur
```

**D. Analyze Logs After Fault**

```bash
# Stop all monitoring (Ctrl+C in terminals)

# Search launch log for key events:
grep -E "control_mode|MODE_CSP|MODE_NA|0x0E080E08|Fault|OPERATION ENABLED" \
  /tmp/launch_*.log

# Extract fault timing:
grep -A 5 -B 5 "0x0E080E08\|Fault state reached" /tmp/launch_*.log

# Correlate with system load:
# Check /tmp/system_load_*.log at fault timestamp

# Search for control mode transitions:
grep -i "control_mode.*MODE" /tmp/launch_*.log | tail -20

# Extract EtherCAT status word changes:
grep "status_word" /tmp/launch_*.log | \
  grep -E "0x1237|0x0000|0x0218" | tail -30
```

**E. Create a Convenient Diagnostic Script**

Save this as `diagnose_fault.sh`:

```bash
#!/bin/bash
# Diagnostic script for drive fault investigation

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/tmp/fault_diagnosis_${TIMESTAMP}"
mkdir -p "${LOG_DIR}"

echo "Starting fault diagnosis with verbose HAL debugging..."
echo "Logs will be saved to: ${LOG_DIR}"
echo "Launch will start in 5 seconds... Press Ctrl+C to cancel"
sleep 5

# Launch with debug and logging
ros2 launch za6_moveit_config teleop_hardware.launch.py \
  use_fake_hardware:=false sim_mode:=false use_sim_time:=false \
  use_rviz:=true \
  servo_config:=servo_config.yaml \
  gamepad_config:=gamepad_config.yaml \
  db:=true \
  hal_debug_level:=5 \
  2>&1 | tee "${LOG_DIR}/launch.log" &

LAUNCH_PID=$!

# Monitor drive state in background
ros2 topic echo /hal_io/drive_state \
  --qos-profile system_default \
  > "${LOG_DIR}/drive_state.log" 2>&1 &
DRIVE_STATE_PID=$!

# Monitor system load
vmstat 1 > "${LOG_DIR}/system_load.log" 2>&1 &
VMSTAT_PID=$!

echo "Diagnosis started. Logs saved to ${LOG_DIR}"
echo "Launch PID: ${LAUNCH_PID}"
echo "Press Ctrl+C to stop all monitoring"

# Wait for user interrupt
trap "kill ${LAUNCH_PID} ${DRIVE_STATE_PID} ${VMSTAT_PID} 2>/dev/null; exit" INT
wait

# Cleanup on exit
kill ${DRIVE_STATE_PID} ${VMSTAT_PID} 2>/dev/null
```

Make it executable: `chmod +x diagnose_fault.sh`

Then run: `./diagnose_fault.sh`

### Step 11: **Isolation Checklist**

Use this checklist to narrow down the cause:

- [ ] **Untimed Trajectories**: Are all `time_from_start` values zero in the YAML file? (Only for captured/replayed solutions)
- [ ] **Idle Fault Observed**: Did fault occur during idle period (no trajectory execution)? (YES - confirmed multiple times)
- [ ] **EtherCAT Master Idle Behavior**: Does the EtherCAT master continue sending cyclic data during idle?
- [ ] **Drive Watchdog Timeout**: What is the drive watchdog timeout setting? Does it match master cycle time?
- [ ] **Error Code Decoded**: What do `0x0E08` and `0x0B00` mean in IS620N documentation?
- [ ] **Timing Pattern**: Does fault occur at consistent time or variable? (Can occur during idle, ~4-10 seconds after last motion)
- [ ] **EtherCAT Communication**: Check for cycle misses or communication loss during idle periods
- [ ] **System Load**: Does fault correlate with CPU/memory/disk spikes?
- [ ] **EtherCAT Communication**: Does `REMOTE` flag drop before fault?
- [ ] **Control Mode Loss Order**: Does mode change before error, or error trigger mode change?
- [ ] **All Drives Simultaneous**: Do all 6 drives fault at exact same time (< 1ms)?
- [ ] **RT Loop Stability**: Is RT loop latency within acceptable bounds (< 100µs)?
- [ ] **Configuration Persistence**: Do CiA 402 parameters remain stable?
- [ ] **External Triggers**: Any other system events coinciding with fault?

### 4. **Run Trajectory Diagnostics Script**

Use the `diagnose_trajectory.py` script to monitor actual velocities/accelerations being sent to the controller:

```bash
source install/setup.bash
ros2 run za6_moveit_config diagnose_trajectory.py
```

Then execute a trajectory from RViz. The script will:
- Log computed velocities/accelerations for each joint
- Compare against configured limits
- Flag any violations
- Check for non-increasing timestamps

### 2. **Check RViz Scaling Sliders**

Before executing, verify RViz Motion Planning panel sliders:
- `Velocity Scaling Factor`: Should be `0.1` or lower
- `Acceleration Scaling Factor`: Should be `0.1` or lower

### 3. **Monitor HAL Drive State**

Check if drives fault immediately or after some motion:
```bash
ros2 topic echo /hal_io/drive_state --qos-profile system_default
```

### 4. **Lower Base Joint Limits (Test)**

Temporarily reduce `max_velocity` and `max_acceleration` in `joint_limits.yaml` to see if faults stop:
- Try halving all limits
- If faults stop, hardware limits are lower than configured

### 5. **Compare MTC vs. Standard Execution**

- If faults only occur with standard RViz "Plan and Execute" → issue with non-MTC trajectory execution
- If faults only occur with MTC → issue with MTC execution capability
- If faults occur with both → issue with base configuration or hardware

## Potential Solutions

### Immediate Fixes

1. **Time-Parameterize Trajectories** (If Using Captured Solutions):
   - Ensure all trajectory waypoints have valid `time_from_start` values
   - Apply `IterativeParabolicTimeParameterization` before saving to YAML
   - See `MTC_EXPERIMENTS.md` for implementation details

2. **Investigate EtherCAT Configuration** (For Control Mode Loss): 
   - Check EtherCAT cycle time settings
   - Verify cable connections and termination
   - Review EtherCAT master configuration for communication stability

2. **Review HAL Control Loop**:
   - Check for RT loop jitter or missed deadlines
   - Verify control mode switching logic doesn't interfere during execution
   - Ensure CiA 402 control mode (`MODE_CSP`) is properly maintained

3. **Add Drive Fault Detection to MoveIt**:
   - Monitor drive state during trajectory execution
   - Abort execution if drives fault (see `MTC_PIPELINE_EXPERIMENT.md` TODO item A)
   - Currently, MoveIt reports success even if drives fault mid-execution

4. **Investigate Error Code `0x0E080E08`**:
   - Look up this error code in IS620N servo documentation
   - May provide specific cause (overcurrent, position error, communication loss, etc.)

### Other Potential Fixes (For Trajectory-Related Issues)

1. **Lower RViz Scaling Sliders**: Ensure they're set to `0.1` or lower before executing
2. **Reduce Base Joint Limits**: Temporarily lower `max_velocity`/`max_acceleration` in `joint_limits.yaml` to match actual HAL limits
3. **Verify Time Parameterization**: Ensure `IterativeParabolicTimeParameterization` is being applied to all trajectories

### Configuration Fixes

1. **Add Trajectory Execution Timeout**: Configure proper execution monitoring in MoveIt
2. **Unify Scaling Configuration**: Ensure all execution paths (MTC and standard) use consistent scaling
3. **Match Hardware Limits**: Update `joint_limits.yaml` to match actual HAL/CiA 402 drive limits

### Code Fixes

1. **Improve Time Parameterization Error Handling**: Don't silently continue if time parameterization fails
2. **Add Pre-Execution Validation**: Check computed velocities/accelerations before sending to controller
3. **Add Drive Fault Detection**: Monitor drive state during execution and abort if faults occur (see `MTC_PIPELINE_EXPERIMENT.md` TODO item A)

## Related Documentation

- **`docs/mtc/MTC_EXPERIMENTS.md`**: Documents previous MTC-specific timing issues (e.g., `TIME_STEP = 0.5` was needed to avoid faults)
- **`docs/mtc/MTC_PIPELINE_EXPERIMENT.md`**: Mentions drive fault handling as a TODO (item A)

## Next Steps

### Priority 1: Untimed Trajectory Fix
1. **Time-parameterize captured solutions**: Ensure all MTC solutions saved to YAML have valid `time_from_start` values before replay
2. **Verify time parameterization in execution**: Confirm `IterativeParabolicTimeParameterization` is being applied in `ExecuteTaskSolutionCapability`

### Priority 2: Control Mode Loss Investigation (CRITICAL - Faults occur during idle!)

1. **Monitor EtherCAT communication during idle**: This is the highest priority since faults occur when robot is not moving
   - **Check if EtherCAT master continues cyclic communication during idle**: Does it stop sending cyclic data when no motion is commanded?
   - **Check drive watchdog timeout settings**: How long can drives go without receiving cyclic data before timing out?
   - Check for EtherCAT cycle misses during idle periods
   - Monitor EtherCAT master cycle time statistics (compare idle vs. active periods)
   - Check for communication timeouts or watchdog triggers
   - Verify EtherCAT cable connections and termination
   - **Review EtherCAT master configuration**: Does it have different behavior during idle vs. active periods?

2. **Check HAL control loop stability during idle**: 
   - Monitor RT loop jitter when robot is idle
   - Check for missed deadlines or context switches
   - Verify HAL components maintain communication during idle

3. **Decode error codes**: Look up `0x0E080E08` and `0x0B000B00` in IS620N servo documentation to identify specific fault causes

4. **Review EtherCAT master configuration**: 
   - Check cycle time settings
   - **Verify watchdog timeout settings** (both master and drive side)
   - **Check if master continues cyclic communication during idle** (critical!)
   - Review synchronization parameters
   - Check for idle-mode behavior differences

5. **Check system resource usage during idle**: 
   - Monitor CPU/memory/disk I/O when robot is idle
   - Check for background processes interfering with EtherCAT

### Priority 3: Execution Monitoring
1. **Implement drive fault detection**: Monitor drive state during trajectory execution and abort on fault (see `MTC_PIPELINE_EXPERIMENT.md` TODO item A)
2. **Fix success reporting**: MoveIt should NOT report success if drives fault mid-execution

### Priority 4: Trajectory Analysis (If Needed)
1. Run `diagnose_trajectory.py` during fault conditions to verify trajectories are within limits
2. Compare HAL drive limits with `joint_limits.yaml` configuration
3. Test with progressively lower scaling factors if control mode issues are resolved but faults persist

