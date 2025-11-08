# Money Converter System

## Project Overview

This project is a Raspberry Pi-based money converter system with a graphical user interface (GUI). It's designed to handle both bills and coins, with functionality for bill-to-bill, bill-to-coin, and coin-to-bill conversions. The system is modular, with separate components for bill handling, coin handling, and the user interface.

The core of the project is written in Python, with the UI built using PyQt5. It interfaces with external hardware, including an Arduino for low-level control of motors and sorters, and a Raspberry Pi for high-level logic. The system also utilizes machine learning models (YOLO) for bill denomination classification and UV counterfeit detection.

## Key Technologies

*   **Programming Language:** Python
*   **UI Framework:** PyQt5
*   **Hardware:** Raspberry Pi, Arduino
*   **Machine Learning:** PyTorch, YOLOv8 (via `ultralytics` package)
*   **Libraries:** `gpiozero`, `pyserial`, `opencv-python`

## Building and Running

### Dependencies

The project requires the following Python libraries:

*   `PyQt5`
*   `ultralytics`
*   `opencv-python`
*   `pyserial`
*   `gpiozero` (for Raspberry Pi)
*   `RPi.GPIO` (for Raspberry Pi)

These can be installed via pip:

```bash
pip install PyQt5 ultralytics opencv-python pyserial gpiozero RPi.GPIO
```

### Running the Application

The main entry point for the application is `UI/main_controller.py`. To run the application, execute the following command from the project root:

```bash
python UI/main_controller.py
```

**Note:** The application is designed to run on a Raspberry Pi with the necessary hardware connected. When run on a different system, it will operate in a mock mode with limited functionality.

### Running Tests

The project contains a `tests` directory with a test file `test_bill_to_coin_cmd.py`. To run the tests, execute the following command from the project root:

```bash
python tests/test_bill_to_coin_cmd.py
```

## Development Conventions

*   **Modularity:** The project is divided into modules for different functionalities (e.g., `bill_handler`, `coin_handler`, `UI`).
*   **Hardware Abstraction:** The `pi_bill_handler.py` and `coin_handler_serial.py` files provide a hardware abstraction layer, allowing the main application logic to be developed and tested independently of the hardware.
*   **Threading:** The application uses `QThread` workers to handle long-running hardware operations, ensuring a responsive UI.
*   **Mocking:** The hardware interface classes include mock objects for development and testing on systems without the required hardware.
*   **UI Design:** The UI is designed using Qt Designer, with the `.ui` files being loaded dynamically.
