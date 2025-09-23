# Linear Actuator + Load Cell Testing

This folder contains Python scripts to test and control a **linear actuator** (via an **IBT-2 motor driver**) and to read force/weight data from an **HX711 load cell amplifier**. 

The scripts are designed for quick experimentation:
- Moving the actuator forward/backward
- Varying actuator speed with software PWM
- Measuring applied force using the load cell

---

## Overview of Scripts

### `HX711.py`
- Interfaces with the **HX711 ADC module** to read data from a load cell.
- Converts raw readings into grams (after calibration).
- Prints force readings with timestamps for a fixed duration (default: 60 seconds).
- Includes calibration constants:
  - `GRAM_CONVERSION`: scales raw ADC values to grams.
  - `INITIAL_OFFSET`: tare/zero offset value.

---

### `actuator_trial.py`
- A **basic actuator test** using the IBT-2 motor driver.
- Moves the actuator:
  1. **Backward** (RPWM = HIGH, LPWM = LOW) for 5 seconds.
  2. **Forward** (RPWM = LOW, LPWM = HIGH) for 5 seconds.
- Stops and disables the driver at the end.

---

### `actuator_speed_control.py`
- Extends the actuator test to include **software PWM speed control**.
- Demonstrates running the actuator at different speeds:
  - 25%, 50%, and 100% duty cycle.
- Moves actuator **DOWN** and then **UP** at each speed.
- Uses a software-timed PWM loop (CPU intensive but works for testing).

---

## Usage

Run any script with Python 3:

```bash
python3 HX711.py              # Read load cell values
python3 actuator_trial.py     # Simple forward/backward test
python3 actuator_speed_control.py   # Speed control with PWM

