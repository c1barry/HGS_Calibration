import gpiod
import time

# === GPIO Setup ===
# Using gpiod (libgpiod) instead of RPi.GPIO for Raspberry Pi GPIO control
chip = gpiod.Chip('gpiochip0')

# Pin assignments for IBT-2 motor driver
RPWM_PIN = 27  # Right PWM input (controls one side of H-bridge)
LPWM_PIN = 22  # Left PWM input (controls other side of H-bridge)
EN_PIN   = 17  # Enable pin (L_EN and R_EN tied together)

# === Request GPIO Lines ===
rpwm = chip.get_line(RPWM_PIN)
lpwm = chip.get_line(LPWM_PIN)
enable = chip.get_line(EN_PIN)

# Configure pins as outputs
rpwm.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)
lpwm.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)
enable.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)

try:
    # --- Enable the motor driver ---
    enable.set_value(1)  # EN = HIGH
    print("Motor driver enabled (EN = HIGH)")

    # --- Move actuator/motor backward ---
    # IBT-2 logic: drive one side HIGH, the other LOW
    print("Moving backward (RPWM HIGH, LPWM LOW)")
    rpwm.set_value(1)
    lpwm.set_value(0)
    time.sleep(5)  # run for 5 seconds

    # --- Move actuator/motor forward ---
    print("Moving forward (LPWM HIGH, RPWM LOW)")
    rpwm.set_value(0)
    lpwm.set_value(1)
    time.sleep(5)  # run for 5 seconds

finally:
    # --- Stop motor and cleanup ---
    print("Stopping motor and disabling driver")
    rpwm.set_value(0)   # both LOW = motor stop
    lpwm.set_value(0)
    enable.set_value(0) # disable driver
    chip.close()        # release GPIO resources

