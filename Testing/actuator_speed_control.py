import gpiod
import time

# === GPIO Setup ===
# Using gpiod (libgpiod) to control Raspberry Pi GPIO lines
chip = gpiod.Chip('gpiochip0')

# GPIO pin assignments (connected to IBT-2 motor driver)
RPWM_PIN = 27  # Right PWM input (controls direction/speed)
LPWM_PIN = 22  # Left PWM input (controls direction/speed)
EN_PIN   = 17  # Enable pin (L_EN and R_EN tied together)

# === Get GPIO lines ===
rpwm = chip.get_line(RPWM_PIN)
lpwm = chip.get_line(LPWM_PIN)
enable = chip.get_line(EN_PIN)

# Configure pins as outputs
rpwm.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)
lpwm.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)
enable.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)

def software_pwm(pin_high, pin_low, duty_cycle, duration, frequency=100):
    """
    Software PWM to control motor speed.
    
    Args:
        pin_high: GPIO line to drive HIGH for motion.
        pin_low: GPIO line to hold LOW (opposite side).
        duty_cycle: Fraction (0–1) of ON time per cycle.
        duration: Total time (s) to run PWM.
        frequency: PWM frequency (Hz).
    """
    period = 1.0 / frequency          # Length of one PWM cycle
    high_time = period * duty_cycle   # Time motor is ON per cycle
    low_time = period - high_time     # Time motor is OFF per cycle
    cycles = int(duration * frequency)

    for _ in range(cycles):
        # Motor ON (forward/reverse depending on which pin is high)
        pin_high.set_value(1)
        pin_low.set_value(0)
        time.sleep(high_time)

        # Motor OFF (both LOW)
        pin_high.set_value(0)
        pin_low.set_value(0)
        time.sleep(low_time)

try:
    # --- Enable motor driver ---
    enable.set_value(1)
    print("Motor driver enabled (EN = HIGH)")

    # Define different speeds to test (duty cycles)
    speeds = [(0.25, "25%"), (0.5, "50%"), (1.0, "100%")]

    # Sweep through speeds in DOWN and UP directions
    for duty, label in speeds:
        # DOWN movement (RPWM HIGH, LPWM LOW)
        print(f"\nMoving DOWN at {label} speed")
        software_pwm(rpwm, lpwm, duty_cycle=duty, duration=3)

        time.sleep(1)  # pause before reversing

        # UP movement (LPWM HIGH, RPWM LOW)
        print(f"Moving UP at {label} speed")
        software_pwm(lpwm, rpwm, duty_cycle=duty, duration=3)

        time.sleep(1)  # pause before changing speed

finally:
    # --- Stop motor and cleanup ---
    print("\nStopping motor and disabling driver")
    rpwm.set_value(0)
    lpwm.set_value(0)
    enable.set_value(0)
    chip.close()  # release GPIO resources

