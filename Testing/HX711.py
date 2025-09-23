import time
import gpiod

# === HX711 Load Cell Amplifier Interface ===
class HX711:
    """
    Interface for reading data from the HX711 24-bit ADC 
    (commonly used with load cells for weight/force measurement).
    """

    def __init__(self, data_pin, clock_pin, chip='gpiochip0'):
        """
        Initialize HX711 on given GPIO pins.
        
        Args:
            data_pin (int): GPIO line number for HX711 data output (DOUT).
            clock_pin (int): GPIO line number for HX711 clock (PD_SCK).
            chip (str): GPIO chip device (default 'gpiochip0').
        """
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        self.chip = gpiod.Chip(chip)

        # Configure GPIO lines
        self.data_line = self.chip.get_line(self.data_pin)
        self.clock_line = self.chip.get_line(self.clock_pin)
        self.data_line.request(consumer="hx711", type=gpiod.LINE_REQ_DIR_IN)
        self.clock_line.request(consumer="hx711", type=gpiod.LINE_REQ_DIR_OUT)

        # Optional: ensure clock starts low (commented for stability testing)
        # self.clock_line.set_value(0)
        # time.sleep(0.0001)

    def read(self):
        """
        Perform one 24-bit reading from HX711.
        
        Returns:
            int: Signed 24-bit raw value from ADC.
        """
        # Wait until HX711 is ready (DOUT goes LOW)
        while self.data_line.get_value():
            pass

        value = 0
        for i in range(24):
            # Pulse clock to shift in one bit
            self.clock_line.set_value(1)
            value = value << 1
            self.clock_line.set_value(0)

            if self.data_line.get_value():
                value += 1

        # Extra clock pulse to set gain/channel
        self.clock_line.set_value(1)
        self.clock_line.set_value(0)

        # Convert unsigned 24-bit to signed integer
        if value & 0x800000:
            value |= ~((1 << 24) - 1)

        return value

    def power_down(self):
        """Power down HX711 (clock HIGH for >60 µs)."""
        self.clock_line.set_value(1)
        time.sleep(0.00006)

    def power_up(self):
        """Power up HX711 (clock LOW)."""
        self.clock_line.set_value(0)
        time.sleep(0.00006)


# === User Calibration Parameters ===
DATA_PIN = 2        # GPIO line for HX711 DOUT
CLOCK_PIN = 3       # GPIO line for HX711 PD_SCK
GRAM_CONVERSION = 1100   # Conversion factor (raw ADC → grams), set via calibration
INITIAL_OFFSET = -7950   # Zero offset (tare), adjust after calibration


def print_force_readings():
    """
    Continuously read force/weight from HX711 and print values for 60 seconds.
    """
    hx = HX711(data_pin=DATA_PIN, clock_pin=CLOCK_PIN)

    # Combine base offset with any extra offset (e.g., skin compliance)
    initial_offset = INITIAL_OFFSET
    skin_offset = 0
    total_offset = initial_offset + skin_offset
    gram_conversion = GRAM_CONVERSION

    try:
        start_time = time.time()
        while time.time() - start_time < 60:  # Run for 60 seconds
            raw_value = hx.read()
            elapsed_time = time.time() - start_time

            # Convert raw ADC value → grams
            weight = (raw_value - total_offset) / gram_conversion

            print(f"{elapsed_time:.2f} seconds, current reading (g): {weight:.2f}")
            time.sleep(0.01)  # Sampling rate (100 Hz max here)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Cleaning up")
        hx.power_down()


# === Main Entry Point ===
if __name__ == "__main__":
    print_force_readings()

