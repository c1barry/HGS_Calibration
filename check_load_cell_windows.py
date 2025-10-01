import time
import random
from datetime import datetime

# === Mock GPIO for Windows Testing ===
class MockGPIO:
    """Mock GPIO interface for Windows testing."""
    
    def __init__(self):
        self.base_value = 25000  # Simulate baseline reading
        self.noise_range = 100   # Simulate noise
        
    def read(self):
        """Simulate HX711 reading with some noise."""
        # Simulate a load cell reading with small variations
        noise = random.randint(-self.noise_range, self.noise_range)
        return self.base_value + noise

# === Calibration Parameters ===
GRAM_CONVERSION = 75000   # Conversion factor (raw ADC → pounds)
INITIAL_OFFSET = 25000    # Zero-load offset

def main():
    """Main function to continuously read and display simulated load cell values."""
    print("=== WINDOWS SIMULATION MODE ===")
    print("This simulates load cell readings for testing purposes")
    print("To run on actual hardware, use this script on a Raspberry Pi")
    print()
    
    try:
        mock_hx = MockGPIO()
        print("Mock HX711 initialized successfully")
    except Exception as e:
        print(f"Error initializing Mock HX711: {e}")
        return
    
    print("Load Cell Reader Started (SIMULATION)")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    print(f"{'Time':<20} {'Raw Value':<12} {'Force (lb)':<12}")
    print("=" * 50)
    
    try:
        while True:
            try:
                # Read simulated value
                raw_value = mock_hx.read()
                
                # Convert to force in pounds
                force_lb = (raw_value - INITIAL_OFFSET) / GRAM_CONVERSION
                
                # Get current timestamp
                current_time = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                # Print formatted output
                print(f"{current_time:<20} {raw_value:<12} {force_lb:<12.3f}")
                
            except Exception as e:
                print(f"Error reading load cell: {e}")
                time.sleep(1)  # Wait before retrying
            
            # Small delay to prevent overwhelming the terminal
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping load cell reader...")
    finally:
        print("Program terminated.")

if __name__ == "__main__":
    main()
