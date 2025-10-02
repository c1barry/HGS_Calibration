import gpiod
import time
from datetime import datetime

# === GPIO Pin Assignments ===
DATA_PIN = 2       # HX711 Data pin
CLOCK_PIN = 3       # HX711 Clock pin

# === Calibration Parameters ===
GRAM_CONVERSION = 75000   # Conversion factor (raw ADC → pounds)
INITIAL_OFFSET = 25000    # Zero-load offset

# === Initialize GPIO Chip ===
chip = gpiod.Chip('gpiochip0')

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
        # Wait for chip ready with timeout
        timeout_count = 0
        while self.data_line.get_value() and timeout_count < 1000:
            timeout_count += 1
            time.sleep(0.001)  # 1ms delay
        
        if timeout_count >= 1000:
            raise Exception("HX711 timeout waiting for chip ready")
            
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
        
        # CRITICAL: Wait for next conversion to be ready
        # HX711 needs time to prepare next sample (typically 100-200ms)
        time.sleep(0.1)  # 100ms delay between reads
        
        return value

    def power_down(self):
        """Power down the HX711."""
        self.clock_line.set_value(1)
        time.sleep(0.00006)

    def power_up(self):
        """Wake up HX711 from power down."""
        self.clock_line.set_value(0)
        time.sleep(0.00006)

def main():
    """Main function to continuously read and display load cell values."""
    try:
        hx = HX711(DATA_PIN, CLOCK_PIN, chip)
        print("HX711 initialized successfully")
    except Exception as e:
        print(f"Error initializing HX711: {e}")
        return
    
    print("Load Cell Reader Started")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    print(f"{'Time':<20} {'Raw Value':<12} {'Force (lb)':<12}")
    print("=" * 50)
    
    try:
        while True:
            try:
                # Read raw value from HX711
                raw_value = hx.read()
                
                # Convert to force in pounds
                force_lb = (raw_value - INITIAL_OFFSET) / GRAM_CONVERSION
                
                # Get current timestamp
                current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # Print formatted output
                print(f"{current_time:<20} {raw_value:<12} {force_lb:<12.3f}")
                
            except Exception as e:
                print(f"Error reading load cell: {e}")
                # Try power cycling the HX711
                try:
                    print("Attempting HX711 power cycle...")
                    hx.power_down()
                    time.sleep(0.1)
                    hx.power_up()
                    time.sleep(0.2)  # Give extra time after power cycle
                except:
                    pass
                time.sleep(0.5)  # Wait before retrying
            
            # Small delay to prevent overwhelming the terminal
            # Note: HX711.read() already includes 100ms delay
            time.sleep(0.05)  # Additional 50ms for terminal display
            
    except KeyboardInterrupt:
        print("\nStopping load cell reader...")
    finally:
        try:
            hx.power_down()
            chip.close()
        except:
            pass
        print("Program terminated.")

if __name__ == "__main__":
    main()
