#!/usr/bin/env python3
"""
Enhanced Load Cell Diagnostic Script
====================================

This script helps diagnose and fix the load cell output doubling issue
by implementing proper HX711 timing and synchronization.

Key improvements:
1. Proper ready-check with timeout
2. Correct conversion timing (200ms for gain=128)
3. Clock line state management
4. Detailed logging of read timing
5. Statistical analysis of readings
"""

import gpiod
import time
import statistics
from datetime import datetime
from collections import deque

# === GPIO Pin Assignments ===
DATA_PIN = 2       # HX711 Data pin
CLOCK_PIN = 3       # HX711 Clock pin

# === Calibration Parameters ===
GRAM_CONVERSION = 75000   # Conversion factor (raw ADC → pounds)
INITIAL_OFFSET = 25000    # Zero-load offset

# === Initialize GPIO Chip ===
chip = gpiod.Chip('gpiochip0')

class HX711Fixed:
    """Fixed HX711 implementation with proper timing and synchronization."""
    
    def __init__(self, data_pin, clock_pin, chip):
        self.data_line = chip.get_line(data_pin)
        self.clock_line = chip.get_line(clock_pin)
        self.data_line.request(consumer="hx711_fixed", type=gpiod.LINE_REQ_DIR_IN)
        self.clock_line.request(consumer="hx711_fixed", type=gpiod.LINE_REQ_DIR_OUT)
        
        # Initialize clock to LOW state
        self.clock_line.set_value(0)
        time.sleep(0.001)  # Give chip time to initialize
        
        # Timing parameters
        self.conversion_time = 0.2  # 200ms for gain=128 (default)
        self.clock_pulse_delay = 0.0001  # 100µs between clock pulses
        self.ready_timeout = 2.0  # 2 second timeout for ready check
        
        print(f"HX711 Fixed initialized: DATA={data_pin}, CLOCK={clock_pin}")
        print(f"Conversion time: {self.conversion_time}s, Clock delay: {self.clock_pulse_delay}s")
    
    def wait_for_ready(self, timeout=None):
        """Wait for HX711 to be ready (DATA line goes LOW)."""
        if timeout is None:
            timeout = self.ready_timeout
            
        start_time = time.time()
        timeout_count = 0
        
        while self.data_line.get_value():
            timeout_count += 1
            if (time.time() - start_time) >= timeout:
                elapsed = time.time() - start_time
                raise TimeoutError(f"HX711 not ready after {elapsed:.2f}s (DATA line stuck HIGH)")
            time.sleep(0.001)
        
        elapsed = time.time() - start_time
        if timeout_count > 0:
            print(f"  Waited {elapsed:.3f}s for chip ready ({timeout_count} checks)")
        
        return elapsed
    
    def read_with_timing(self):
        """Read HX711 with detailed timing information."""
        read_start = time.time()
        
        # Step 1: Wait for chip ready
        ready_time = self.wait_for_ready()
        
        # Step 2: Read 24 bits
        bit_read_start = time.time()
        value = 0
        
        for bit in range(24):
            # Clock HIGH
            self.clock_line.set_value(1)
            time.sleep(self.clock_pulse_delay)
            
            # Shift and read bit
            value = value << 1
            if self.data_line.get_value():
                value += 1
            
            # Clock LOW
            self.clock_line.set_value(0)
            time.sleep(self.clock_pulse_delay)
        
        bit_read_time = time.time() - bit_read_start
        
        # Step 3: 25th pulse for gain/channel selection
        self.clock_line.set_value(1)
        time.sleep(self.clock_pulse_delay)
        self.clock_line.set_value(0)
        
        # Step 4: Convert to signed 24-bit integer
        if value & 0x800000:
            value |= ~((1 << 24) - 1)
        
        total_read_time = time.time() - read_start
        
        return {
            'value': value,
            'ready_time': ready_time,
            'bit_read_time': bit_read_time,
            'total_read_time': total_read_time,
            'timestamp': read_start
        }
    
    def read(self):
        """Standard read method for compatibility."""
        result = self.read_with_timing()
        return result['value']
    
    def power_down(self):
        """Power down the HX711."""
        self.clock_line.set_value(1)
        time.sleep(0.00006)
    
    def power_up(self):
        """Wake up HX711 from power down."""
        self.clock_line.set_value(0)
        time.sleep(0.00006)

def analyze_readings(readings, window_size=10):
    """Analyze readings for patterns and anomalies."""
    if len(readings) < window_size:
        return "Insufficient data for analysis"
    
    # Convert to list for analysis
    values = [r['value'] for r in readings[-window_size:]]
    forces = [(r['value'] - INITIAL_OFFSET) / GRAM_CONVERSION for r in readings[-window_size:]]
    
    # Calculate statistics
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 0
    mean_force = statistics.mean(forces)
    std_force = statistics.stdev(forces) if len(forces) > 1 else 0
    
    # Check for doubling pattern
    diffs = [abs(values[i] - values[i-1]) for i in range(1, len(values))]
    avg_diff = statistics.mean(diffs) if diffs else 0
    
    # Look for suspicious patterns
    analysis = {
        'mean_raw': mean_val,
        'std_raw': std_val,
        'mean_force': mean_force,
        'std_force': std_force,
        'avg_diff': avg_diff,
        'cv_percent': (std_val / abs(mean_val) * 100) if mean_val != 0 else 0
    }
    
    return analysis

def main():
    """Main diagnostic function."""
    print("=== Load Cell Doubling Diagnostic ===")
    print("This script will help identify the cause of output doubling")
    print()
    
    try:
        hx = HX711Fixed(DATA_PIN, CLOCK_PIN, chip)
        print("HX711 initialized successfully")
    except Exception as e:
        print(f"Error initializing HX711: {e}")
        return
    
    # Test parameters
    test_duration = 30  # seconds
    readings = deque(maxlen=100)  # Keep last 100 readings
    
    print(f"\nStarting {test_duration}s diagnostic test...")
    print("=" * 80)
    print(f"{'Time':<8} {'Raw':<10} {'Force':<8} {'Ready':<6} {'Total':<6} {'Analysis'}")
    print("=" * 80)
    
    start_time = time.time()
    last_read_time = 0
    
    try:
        while (time.time() - start_time) < test_duration:
            try:
                # Read with timing information
                result = hx.read_with_timing()
                readings.append(result)
                
                # Calculate force
                force_lb = (result['value'] - INITIAL_OFFSET) / GRAM_CONVERSION
                
                # Calculate time since last read
                time_since_last = result['timestamp'] - last_read_time if last_read_time > 0 else 0
                last_read_time = result['timestamp']
                
                # Analyze recent readings
                analysis = analyze_readings(readings)
                
                # Format output
                elapsed = time.time() - start_time
                analysis_str = ""
                if isinstance(analysis, dict):
                    if analysis['cv_percent'] > 5:  # High coefficient of variation
                        analysis_str = f"HIGH_VAR({analysis['cv_percent']:.1f}%)"
                    if analysis['avg_diff'] > abs(analysis['mean_raw']) * 0.1:  # Large differences
                        analysis_str += " LARGE_DIFF"
                
                print(f"{elapsed:6.1f}s {result['value']:<10} {force_lb:6.2f} "
                      f"{result['ready_time']:5.3f} {result['total_read_time']:5.3f} {analysis_str}")
                
                # Wait for proper conversion time
                time.sleep(max(0, self.conversion_time - result['total_read_time']))
                
            except TimeoutError as e:
                print(f"TIMEOUT: {e}")
                # Try power cycling
                try:
                    hx.power_down()
                    time.sleep(0.1)
                    hx.power_up()
                    time.sleep(0.2)
                except:
                    pass
                time.sleep(0.5)
                
            except Exception as e:
                print(f"ERROR: {e}")
                time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    
    finally:
        # Final analysis
        print("\n" + "=" * 80)
        print("FINAL ANALYSIS:")
        
        if len(readings) >= 10:
            final_analysis = analyze_readings(readings)
            if isinstance(final_analysis, dict):
                print(f"Mean raw value: {final_analysis['mean_raw']:.0f}")
                print(f"Standard deviation: {final_analysis['std_raw']:.0f}")
                print(f"Coefficient of variation: {final_analysis['cv_percent']:.2f}%")
                print(f"Mean force: {final_analysis['mean_force']:.3f} lb")
                print(f"Force std dev: {final_analysis['std_force']:.3f} lb")
                print(f"Average difference between readings: {final_analysis['avg_diff']:.0f}")
                
                # Diagnosis
                print("\nDIAGNOSIS:")
                if final_analysis['cv_percent'] > 10:
                    print("❌ HIGH VARIABILITY - Possible timing issues or electrical noise")
                elif final_analysis['cv_percent'] > 5:
                    print("⚠️  MODERATE VARIABILITY - May indicate occasional timing problems")
                else:
                    print("✅ LOW VARIABILITY - Timing appears correct")
                
                if final_analysis['avg_diff'] > abs(final_analysis['mean_raw']) * 0.2:
                    print("❌ LARGE DIFFERENCES - Possible doubling or reading errors")
                else:
                    print("✅ STABLE READINGS - No obvious doubling detected")
        
        try:
            hx.power_down()
            chip.close()
        except:
            pass
        print("\nDiagnostic complete.")

if __name__ == "__main__":
    main()
