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

# === Enhanced HX711 Load Cell Interface with Debugging ===
class HX711Debug:
    """Enhanced HX711 interface with comprehensive debugging."""

    def __init__(self, data_pin, clock_pin, chip):
        self.data_line = chip.get_line(data_pin)
        self.clock_line = chip.get_line(clock_pin)
        self.data_line.request(consumer="hx711_debug", type=gpiod.LINE_REQ_DIR_IN)
        self.clock_line.request(consumer="hx711_debug", type=gpiod.LINE_REQ_DIR_OUT)
        
        # Initialize clock to LOW
        self.clock_line.set_value(0)
        time.sleep(0.001)  # Give chip time to initialize
        
        print(f"HX711 initialized on DATA={data_pin}, CLOCK={clock_pin}")

    def check_data_line_state(self):
        """Check if data line is stuck HIGH (chip not ready)."""
        return self.data_line.get_value()

    def power_cycle(self):
        """Power cycle the HX711 chip."""
        print("Power cycling HX711...")
        # Power down
        self.clock_line.set_value(1)
        time.sleep(0.1)  # Longer power down
        
        # Power up
        self.clock_line.set_value(0)
        time.sleep(0.1)  # Longer power up
        print("Power cycle complete")

    def read_with_debug(self, max_wait_time=2.0):
        """Read HX711 with detailed debugging information."""
        print("Starting HX711 read...")
        
        # Check initial data line state
        initial_data_state = self.data_line.get_value()
        print(f"Initial DATA line state: {initial_data_state}")
        
        if initial_data_state == 0:
            print("DATA line is LOW - chip appears ready")
        else:
            print("DATA line is HIGH - waiting for chip ready...")
        
        # Wait for chip ready with detailed timing
        start_time = time.time()
        timeout_count = 0
        
        while self.data_line.get_value() and (time.time() - start_time) < max_wait_time:
            timeout_count += 1
            if timeout_count % 100 == 0:  # Print every 100ms
                elapsed = time.time() - start_time
                print(f"Still waiting... {elapsed:.2f}s elapsed, DATA={self.data_line.get_value()}")
            time.sleep(0.001)
        
        elapsed_time = time.time() - start_time
        
        if elapsed_time >= max_wait_time:
            print(f"TIMEOUT after {elapsed_time:.2f}s - DATA line still HIGH")
            print("Possible causes:")
            print("  1. HX711 not powered (check VCC connection)")
            print("  2. Wrong GPIO pins (check DATA/CLOCK wiring)")
            print("  3. Defective HX711 chip")
            print("  4. Load cell not connected properly")
            print("  5. Clock line stuck HIGH")
            return None
        
        print(f"Chip ready after {elapsed_time:.3f}s")
        
        # Read 24 bits
        value = 0
        print("Reading 24 bits...")
        
        for bit in range(24):
            # Clock HIGH
            self.clock_line.set_value(1)
            time.sleep(0.0001)  # Small delay for stability
            
            # Shift and read bit
            value = value << 1
            if self.data_line.get_value():
                value += 1
            
            # Clock LOW
            self.clock_line.set_value(0)
            time.sleep(0.0001)
            
            if bit % 8 == 7:  # Print every 8 bits
                print(f"  Bits {bit-7}-{bit}: {value & 0xFF:08b}")
        
        # 25th pulse for gain/channel selection
        self.clock_line.set_value(1)
        time.sleep(0.0001)
        self.clock_line.set_value(0)
        
        # Convert to signed 24-bit integer
        if value & 0x800000:
            value |= ~((1 << 24) - 1)
        
        print(f"Raw value: {value} (0x{value:06x})")
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
    """Main function with comprehensive debugging."""
    print("=== HX711 Load Cell Debugger ===")
    print("This will help diagnose HX711 communication issues")
    print()
    
    try:
        hx = HX711Debug(DATA_PIN, CLOCK_PIN, chip)
        print("HX711 initialized successfully")
    except Exception as e:
        print(f"Error initializing HX711: {e}")
        print("Check:")
        print("  1. GPIO permissions (try running with sudo)")
        print("  2. GPIO pins are not in use by another process")
        print("  3. Correct pin numbers")
        return
    
    print("\n=== Diagnostic Tests ===")
    
    # Test 1: Check data line state
    print("\n1. Checking DATA line state...")
    data_state = hx.check_data_line_state()
    print(f"   DATA line: {'HIGH' if data_state else 'LOW'}")
    
    if data_state:
        print("   WARNING: DATA line is HIGH - chip may not be ready")
        print("   Trying power cycle...")
        hx.power_cycle()
        data_state = hx.check_data_line_state()
        print(f"   After power cycle, DATA line: {'HIGH' if data_state else 'LOW'}")
    
    # Test 2: Try reading with debug
    print("\n2. Attempting to read from HX711...")
    try:
        raw_value = hx.read_with_debug()
        if raw_value is not None:
            force_lb = (raw_value - INITIAL_OFFSET) / GRAM_CONVERSION
            print(f"SUCCESS! Raw: {raw_value}, Force: {force_lb:.3f} lb")
            
            # Test continuous reading
            print("\n3. Testing continuous reading (5 samples)...")
            for i in range(5):
                raw_value = hx.read_with_debug()
                if raw_value is not None:
                    force_lb = (raw_value - INITIAL_OFFSET) / GRAM_CONVERSION
                    print(f"   Sample {i+1}: Raw={raw_value}, Force={force_lb:.3f} lb")
                else:
                    print(f"   Sample {i+1}: FAILED")
                time.sleep(0.1)
        else:
            print("FAILED: Could not read from HX711")
            
    except Exception as e:
        print(f"Error during read: {e}")
    
    finally:
        try:
            hx.power_down()
            chip.close()
        except:
            pass
        print("\nDebug session complete.")

if __name__ == "__main__":
    main()
