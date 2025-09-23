import gpiod
import time
import threading
import csv
from datetime import datetime

# === GPIO Pin Assignments ===
RPWM_PIN = 27      # IBT-2 Right PWM (Retract)
LPWM_PIN = 22      # IBT-2 Left PWM (Extend)
EN_PIN = 17        # Motor driver enable pin
DATA_PIN = 2       # HX711 Data pin
CLOCK_PIN = 3      # HX711 Clock pin

# === Calibration Parameters ===
GRAM_CONVERSION = 75000   # Conversion factor (raw ADC → pounds)
INITIAL_OFFSET = 25000    # Zero-load offset

# === Initialize GPIO Chip ===
chip = gpiod.Chip('gpiochip0')

# === Test Configurations ===
TEST_DURATION = 10        # Duration of each test (seconds)
MAX_FORCE_DURATION = 3    # Hold time at maximum force (seconds)
REPETITIONS = 10          # Number of test repetitions
TEST_MODE = 1             # Mode: 1=gradual, 2=step, 3=sudden
FIXED_DUTY = 1            # Fixed duty cycle for manual override


# === HX711 Load Cell Interface ===
class HX711:
    """Interface for HX711 24-bit ADC (load cell amplifier)."""

    def __init__(self, data_pin, clock_pin, chip):
        self.data_line = chip.get_line(data_pin)
        self.clock_line = chip.get_line(clock_pin)
        self.data_line.request(consumer="hx711", type=gpiod.LINE_REQ_DIR_IN)
        self.clock_line.request(consumer="hx711", type=gpiod.LINE_REQ_DIR_OUT)

    def read(self):
        """Read a single 24-bit sample from HX711."""
        while self.data_line.get_value():
            pass  # wait for chip ready
        value = 0
        for _ in range(24):
            self.clock_line.set_value(1)
            value = value << 1
            self.clock_line.set_value(0)
            if self.data_line.get_value():
                value += 1
        # 25th pulse sets gain/channel
        self.clock_line.set_value(1)
        self.clock_line.set_value(0)

        # Convert to signed 24-bit integer
        if value & 0x800000:
            value |= ~((1 << 24) - 1)
        return value

    def power_down(self):
        """Power down the HX711."""
        self.clock_line.set_value(1)
        time.sleep(0.00006)

    def power_up(self):
        """Wake up HX711 from power down."""
        self.clock_line.set_value(0)
        time.sleep(0.00006)


# === Linear Actuator Driver (IBT-2) ===
class LinearActuator:
    """Controls a linear actuator via IBT-2 H-Bridge motor driver."""

    def __init__(self, rpwm_pin, lpwm_pin, en_pin, chip):
        self.rpwm = chip.get_line(rpwm_pin)
        self.lpwm = chip.get_line(lpwm_pin)
        self.enable = chip.get_line(en_pin)

        self.rpwm.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)
        self.lpwm.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)
        self.enable.request(consumer="ibt2", type=gpiod.LINE_REQ_DIR_OUT)

    def enable_motor(self):
        """Enable the motor driver (EN=HIGH)."""
        self.enable.set_value(1)
        print("Motor driver enabled (EN = HIGH)")

    def disable_motor(self):
        """Disable motor driver and stop actuator."""
        print("Stopping motor and disabling driver")
        self.rpwm.set_value(0)
        self.lpwm.set_value(0)
        self.enable.set_value(0)

    def stop(self):
        """Stop actuator movement (both outputs LOW)."""
        print("Stopping motor")
        self.rpwm.set_value(0)
        self.lpwm.set_value(0)

    def pwm_control_extend(self, duty_cycle, duration, frequency=100):
        """Manually extend actuator using PWM for a set duration."""
        period = 1.0 / frequency
        high_time = period * duty_cycle
        low_time = period - high_time
        cycles = int(duration * frequency)

        print(f"Extending at {duty_cycle*100:.0f}% duty for {duration:.2f}s")
        for _ in range(cycles):
            self.rpwm.set_value(0)
            self.lpwm.set_value(1)
            time.sleep(high_time)
            self.lpwm.set_value(0)
            time.sleep(low_time)

    def pwm_control_retract(self, duty_cycle, duration, frequency=100):
        """Manually retract actuator using PWM for a set duration."""
        period = 1.0 / frequency
        high_time = period * duty_cycle
        low_time = period - high_time
        cycles = int(duration * frequency)

        print(f"Retracting at {duty_cycle*100:.0f}% duty for {duration:.2f}s")
        for _ in range(cycles):
            self.rpwm.set_value(1)
            self.lpwm.set_value(0)
            time.sleep(high_time)
            self.rpwm.set_value(0)
            time.sleep(low_time)


# === Shared State (accessed by multiple threads) ===
current_force = 0.0     # latest measured force (pounds)
current_duty = FIXED_DUTY
current_dir = 0         # -1=retract, 0=stop, +1=extend
_state_lock = threading.Lock()


# === Background Threads ===
def read_force_continuous(hx, stop_event, mechanical_noise_factor=1, samples=1, period_s=0.01):
    """Continuously read force from HX711 in a background thread."""
    global current_force
    while not stop_event.is_set():
        reading = sum(hx.read() for _ in range(samples)) / samples
        current_force = (reading - INITIAL_OFFSET) / (GRAM_CONVERSION * mechanical_noise_factor)
        print(f"Measured force: {current_force:.2f} lb")
        time.sleep(period_s)


def actuator_pwm_loop(actuator, stop_event, frequency=50, force_threshold=-100):
    """
    Continuously drive actuator with PWM.
    Includes safety override: retract if force exceeds threshold.
    """
    global current_force, current_dir, current_duty
    period = 1.0 / frequency

    while not stop_event.is_set():
        with _state_lock:
            duty = current_duty
            direction = current_dir
            force = current_force

        # --- Safety override ---
        if force < force_threshold:
            print(f"[SAFETY] Force {force:.2f} lb > {force_threshold} lb! RETRACTING.")
            with _state_lock:
                current_dir = -1     # retract
                current_duty = 1.0   # full duty
            duty = 1.0
            direction = -1

        # --- No motion case ---
        if duty <= 0 or direction == 0:
            actuator.rpwm.set_value(0)
            actuator.lpwm.set_value(0)
            time.sleep(period)
            continue

        # --- PWM drive (extend/retract) ---
        high_time = period * max(0.0, min(duty, 1.0))
        low_time = period - high_time

        if direction > 0:  # extend
            actuator.rpwm.set_value(0)
            actuator.lpwm.set_value(1)
            time.sleep(high_time)
            actuator.lpwm.set_value(0)
            time.sleep(low_time)
        else:              # retract
            actuator.rpwm.set_value(1)
            actuator.lpwm.set_value(0)
            time.sleep(high_time)
            actuator.rpwm.set_value(0)
            time.sleep(low_time)


# === Feedback Controller (P-control) ===
def feedback_extend_to_target(
    actuator, target_force, tolerance=0.05, update_interval=0.05, max_seconds=1.0, Kp=0.005
):
    """
    Move actuator until target force is reached using proportional control.
    Stops when within tolerance or after timeout.
    """
    global current_dir, current_duty

    actuator.enable_motor()
    print(f"[Feedback] Driving until target ~{target_force} lb (Kp={Kp})")

    start_ts = time.time()

    try:
        while True:
            error = target_force - current_force

            # --- Stop if within tolerance ---
            if abs(error) <= tolerance:
                with _state_lock:
                    current_dir = 0
                    current_duty = 0
                print(f"[Feedback] Target reached: {current_force:.2f} lb")
                break

            # --- Timeout safety ---
            if (time.time() - start_ts) > max_seconds:
                with _state_lock:
                    current_dir = 0
                    current_duty = 0
                print("[Feedback] Timeout reached, stopping")
                break

            # --- P-control (duty proportional to error) ---
            duty = min(1.0, Kp * abs(error))   # clamp at 100%
            direction = -1 if error > 0 else 1  # extend if target > force, else retract

            with _state_lock:
                current_dir = direction
                current_duty = duty

            print(f"[Feedback] error={error:.2f}, duty={duty:.2f}, dir={direction}")

            time.sleep(update_interval)

    finally:
        with _state_lock:
            current_dir = 0
            current_duty = 0
        actuator.stop()


# === Main Entry Point ===
if __name__ == "__main__":
    actuator = LinearActuator(RPWM_PIN, LPWM_PIN, EN_PIN, chip)
    hx = HX711(DATA_PIN, CLOCK_PIN, chip)

    # Sequence of target forces for testing (negative = compression load)
    TARGET_FORCES = [-1, -2, -3, -4, -3, -2, -1]

    try:
        # --- Start background threads ---
        read_stop_event = threading.Event()
        actuator_stop_event = threading.Event()

        reader_thread = threading.Thread(
            target=read_force_continuous, args=(hx, read_stop_event)
        )
        reader_thread.start()

        actuator_thread = threading.Thread(
            target=actuator_pwm_loop, args=(actuator, actuator_stop_event)
        )
        actuator_thread.start()

        # --- Perform test repetitions ---
        for rep in range(1, REPETITIONS + 1):
            current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            filename = f"autopusher_feedback_seq_rep{rep}_{current_time}.csv"

            with open(filename, mode='w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(['Time (s)', 'Force (lb)', 'Target (lb)'])
                start_time = time.time()

                # logger thread to save data to CSV
                log_stop_event = threading.Event()
                def logger():
                    while not log_stop_event.is_set():
                        timestamp = time.time() - start_time
                        with _state_lock:
                            f = current_force
                        current_target = target_holder[0] if target_holder else None
                        csv_writer.writerow([timestamp, f, current_target])
                        time.sleep(0.01)

                target_holder = [None]  # shared mutable holder for current target
                logger_thread = threading.Thread(target=logger)
                logger_thread.start()

                print(f"\n=== Starting repetition {rep}/{REPETITIONS} (Sequential targets) ===")

                # Sequentially go through all targets
                for tgt in TARGET_FORCES:
                    target_holder[0] = tgt
                    print(f"\n[Sequence] Moving to target {tgt} lb")
                    feedback_extend_to_target(actuator, tgt)

                # stop logger after sequence
                log_stop_event.set()
                logger_thread.join()

        # --- Stop background threads ---
        read_stop_event.set()
        actuator_stop_event.set()
        reader_thread.join()
        actuator_thread.join()

    except KeyboardInterrupt:
        print("Interrupted by user.")
        actuator.disable_motor()
    finally:
        hx.power_down()
        chip.close()
        print("Program terminated.")

