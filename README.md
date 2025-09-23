# Hand Grip Strength (HGS) Measurement Setup

This repository contains all the files, CAD models, wiring information, and test code required to build and run a Raspberry Pi–based Hand Grip Strength measurement system. The setup combines a linear actuator, a load cell with HX711 amplifier, and 3D/2D printed parts to collect grip force measurements in different configurations.

---

## Quick Start

1. **Assemble hardware**
   - Laser cut brackets from `2D_Printing/`
   - 3D print parts from `3D_Printing/`
   - Wire Raspberry Pi, IBT-2 motor driver, actuator, HX711, and load cell following `Setup_and_Wiring.pdf`

2. **Verify components**
   - Run scripts in `Testing/`:
     - `HX711.py` → check load cell readings
     - `actuator_trial.py` → test actuator forward/backward
     - `actuator_speed_control.py` → test actuator speed with software PWM

3. **Run main experiment**
   - Execute:
     ```bash
     python3 RPi5_LoadCell_LActuator_csv.py
     ```
   - CSV files will be created with timestamps, measured forces, and target forces
   - Follow `dyna_data_collection_guide.pdf` for grip protocols

---

## Repository Structure

- **2D_Printing/**  
  Contains Inkscape files used for laser cutting the square and triangular brackets.

- **3D_Printing/**  
  Contains OBJ files for 3D printing custom grips and fixtures.

- **Testing/**  
  Contains Python scripts for component-level testing:  
  - `actuator_speed_control.py` → Software PWM control for actuator speed  
  - `actuator_trial.py` → Basic actuator forward/backward test  
  - `HX711.py` → Load cell (HX711) readout test  

- **dyna_data_collection_guide.pdf**  
  Explains grip protocols and data collection procedures.

- **Setup_and_Wiring.pdf**  
  Provides hardware wiring and assembly instructions.

- **RPi5_LoadCell_LActuator_csv.py**  
  Main Python script that integrates actuator + load cell into a closed-loop system, logs force data to CSV, and automates test repetitions.




---

## Code Overview

The main Python file `RPi5_LoadCell_LActuator_csv.py` integrates the actuator and load cell into a closed-loop system. It continuously reads force values from the HX711 load cell, controls the actuator via the IBT-2 motor driver, and uses a proportional feedback controller to drive the actuator until a target force is reached. Targets are defined as a sequence, and the actuator moves through them automatically. Safety overrides are implemented so that if the measured force exceeds a threshold, the actuator retracts immediately. Each run produces CSV logs containing timestamps, measured forces, and target forces, making it suitable for analysis in Python, MATLAB, or Excel. Repetitions of the test sequence are supported, and logs are stored with timestamps in filenames for organization.

---

## Workflow

1. **Print and cut parts** → use files in `2D_Printing/` and `3D_Printing/` 
2. **Assemble setup** → follow `Setup_and_Wiring.pdf` for correct wiring and hardware assembly 
3. **Test components** → run the scripts in `Testing/` to confirm functionality 
4. **Run full experiment** → use `RPi5_LoadCell_LActuator_csv.py` to record force sequences automatically 
5. **Collect data** → follow `dyna_data_collection_guide.pdf` to maintain consistent protocols 

---

## Notes

- Adjust GPIO pin numbers in the scripts to match your wiring 
- Calibrate `GRAM_CONVERSION` and `INITIAL_OFFSET` in `HX711.py` or main script for accurate force readings 
- Actuator forces can be high → secure the test rig and check safety override before running 
- CSV log files will accumulate quickly; store them in a dedicated folder for analysis 

---

## License

This project is provided for research and educational purposes. You are free to modify, adapt, and use the code and designs for your own experiments, but it comes with no warranty or guarantee of safety. Use at your own risk.

