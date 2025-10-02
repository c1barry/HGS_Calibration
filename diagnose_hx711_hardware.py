import gpiod
import time
from datetime import datetime

# === GPIO Pin Assignments ===
DATA_PIN = 2       # HX711 Data pin
CLOCK_PIN = 3       # HX711 Clock pin

# === Initialize GPIO Chip ===
chip = gpiod.Chip('gpiochip0')

class HX711Diagnostic:
    """Enhanced HX711 diagnostic with hardware testing."""

    def __init__(self, data_pin, clock_pin, chip):
        self.data_line = chip.get_line(data_pin)
        self.clock_line = chip.get_line(clock_pin)
        self.data_line.request(consumer="hx711_diag", type=gpiod.LINE_REQ_DIR_IN)
        self.clock_line.request(consumer="hx711_diag", type=gpiod.LINE_REQ_DIR_OUT)
        
        # Initialize clock to LOW
        self.clock_line.set_value(0)
        time.sleep(0.01)
        
        print(f"HX711 Diagnostic initialized on DATA={data_pin}, CLOCK={clock_pin}")

    def test_gpio_pins(self):
        """Test GPIO pin functionality."""
        print("\n=== GPIO Pin Test ===")
        
        # Test CLOCK pin (output)
        print("Testing CLOCK pin (output)...")
        for i in range(5):
            self.clock_line.set_value(1)
            time.sleep(0.01)
            self.clock_line.set_value(0)
            time.sleep(0.01)
        print("CLOCK pin test complete")
        
        # Test DATA pin (input)
        print("Testing DATA pin (input)...")
        for i in range(5):
            data_val = self.data_line.get_value()
            print(f"  DATA pin value: {data_val}")
            time.sleep(0.1)
        print("DATA pin test complete")

    def test_hx711_communication(self):
        """Test HX711 communication with detailed timing."""
        print("\n=== HX711 Communication Test ===")
        
        # Test 1: Check initial state
        print("1. Checking initial DATA line state...")
        initial_data = self.data_line.get_value()
        print(f"   Initial DATA: {'HIGH' if initial_data else 'LOW'}")
        
        if initial_data:
            print("   WARNING: DATA line is HIGH - chip may not be ready")
            return False
        
        # Test 2: Try single read with detailed timing
        print("2. Attempting single read with timing analysis...")
        start_time = time.time()
        
        # Wait for ready with detailed feedback
        timeout_count = 0
        while self.data_line.get_value() and timeout_count < 2000:  # 2 second timeout
            timeout_count += 1
            if timeout_count % 200 == 0:  # Every 200ms
                elapsed = time.time() - start_time
                print(f"   Still waiting... {elapsed:.2f}s, DATA={self.data_line.get_value()}")
            time.sleep(0.001)
        
        elapsed_time = time.time() - start_time
        
        if timeout_count >= 2000:
            print(f"   TIMEOUT after {elapsed_time:.2f}s")
            print("   Possible causes:")
            print("     - HX711 not powered (check VCC)")
            print("     - Wrong GPIO pins")
            print("     - Defective HX711 chip")
            print("     - Clock line stuck HIGH")
            return False
        
        print(f"   Chip ready after {elapsed_time:.3f}s")
        
        # Test 3: Read with bit-by-bit analysis
        print("3. Reading 24 bits...")
        value = 0
        for bit in range(24):
            # Clock HIGH
            self.clock_line.set_value(1)
            time.sleep(0.0001)
            
            # Shift and read bit
            value = value << 1
            if self.data_line.get_value():
                value += 1
            
            # Clock LOW
            self.clock_line.set_value(0)
            time.sleep(0.0001)
            
            if bit % 8 == 7:  # Print every 8 bits
                print(f"   Bits {bit-7}-{bit}: {value & 0xFF:08b}")
        
        # 25th pulse
        self.clock_line.set_value(1)
        time.sleep(0.0001)
        self.clock_line.set_value(0)
        
        # Convert to signed
        if value & 0x800000:
            value |= ~((1 << 24) - 1)
        
        print(f"   Raw value: {value} (0x{value:06x})")
        
        # Test 4: Check DATA line after read
        print("4. Checking DATA line after read...")
        time.sleep(0.01)  # Small delay
        post_read_data = self.data_line.get_value()
        print(f"   DATA after read: {'HIGH' if post_read_data else 'LOW'}")
        
        return True

    def test_continuous_reading(self, num_reads=5):
        """Test continuous reading with different delays."""
        print(f"\n=== Continuous Reading Test ({num_reads} reads) ===")
        
        for i in range(num_reads):
            print(f"\nRead {i+1}/{num_reads}:")
            
            # Check DATA line before read
            data_before = self.data_line.get_value()
            print(f"  DATA before: {'HIGH' if data_before else 'LOW'}")
            
            if data_before:
                print("  DATA is HIGH - chip not ready, skipping this read")
                time.sleep(0.2)
                continue
            
            # Try to read
            try:
                start_time = time.time()
                timeout_count = 0
                
                while self.data_line.get_value() and timeout_count < 1000:
                    timeout_count += 1
                    time.sleep(0.001)
                
                if timeout_count >= 1000:
                    print("  TIMEOUT - chip not ready")
                    time.sleep(0.2)
                    continue
                
                # Read 24 bits
                value = 0
                for _ in range(24):
                    self.clock_line.set_value(1)
                    value = value << 1
                    self.clock_line.set_value(0)
                    if self.data_line.get_value():
                        value += 1
                
                # 25th pulse
                self.clock_line.set_value(1)
                self.clock_line.set_value(0)
                
                # Convert to signed
                if value & 0x800000:
                    value |= ~((1 << 24) - 1)
                
                elapsed = time.time() - start_time
                print(f"  SUCCESS: {value} (took {elapsed:.3f}s)")
                
                # Wait different amounts to test timing
                if i < 2:
                    delay = 0.05  # 50ms
                elif i < 4:
                    delay = 0.1   # 100ms
                else:
                    delay = 0.2   # 200ms
                
                print(f"  Waiting {delay*1000:.0f}ms before next read...")
                time.sleep(delay)
                
            except Exception as e:
                print(f"  ERROR: {e}")
                time.sleep(0.2)

    def power_cycle_test(self):
        """Test power cycling functionality."""
        print("\n=== Power Cycle Test ===")
        
        print("Powering down HX711...")
        self.clock_line.set_value(1)
        time.sleep(0.1)
        
        print("Powering up HX711...")
        self.clock_line.set_value(0)
        time.sleep(0.2)
        
        # Check DATA line after power cycle
        data_after = self.data_line.get_value()
        print(f"DATA after power cycle: {'HIGH' if data_after else 'LOW'}")
        
        if data_after:
            print("WARNING: DATA still HIGH after power cycle")
        else:
            print("SUCCESS: DATA is LOW after power cycle")

    def power_down(self):
        """Power down the HX711."""
        self.clock_line.set_value(1)
        time.sleep(0.00006)

    def power_up(self):
        """Wake up HX711 from power down."""
        self.clock_line.set_value(0)
        time.sleep(0.00006)

def main():
    """Main diagnostic function."""
    print("=== HX711 Hardware Diagnostic Tool ===")
    print("This will help identify hardware vs software issues")
    print()
    
    try:
        hx = HX711Diagnostic(DATA_PIN, CLOCK_PIN, chip)
    except Exception as e:
        print(f"Error initializing HX711: {e}")
        print("Check:")
        print("  1. GPIO permissions (run with sudo)")
        print("  2. GPIO pins not in use by another process")
        print("  3. Correct pin numbers")
        return
    
    try:
        # Run all diagnostic tests
        hx.test_gpio_pins()
        hx.test_hx711_communication()
        hx.test_continuous_reading()
        hx.power_cycle_test()
        
        print("\n=== Diagnostic Complete ===")
        print("Review the results above to identify the issue:")
        print("- If GPIO tests fail: Check wiring and pin assignments")
        print("- If communication fails: Check power supply and HX711 chip")
        print("- If continuous reading fails: Timing or power stability issue")
        
    except KeyboardInterrupt:
        print("\nDiagnostic interrupted by user")
    finally:
        try:
            hx.power_down()
            chip.close()
        except:
            pass
        print("Diagnostic complete.")

if __name__ == "__main__":
    main()
