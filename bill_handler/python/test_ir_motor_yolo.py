# tests/test_ir_motor_yolo.py
from gpiozero import Motor, PWMOutputDevice, DigitalInputDevice, LED
from time import sleep
import cv2
import os
from ultralytics import YOLO

# --- Pin configuration (adjust to your wiring) ---
MOTOR_FORWARD_PIN = 23
MOTOR_BACKWARD_PIN = 24
MOTOR_ENABLE_PIN = 18   # ENA pin (PWM capable)
IR_SENSOR_PIN = 17      # IR sensor signal pin (active-low)
WHITE_LED_PIN = 27      # White LED pin

# --- Hardware setup ---
motor = Motor(forward=MOTOR_FORWARD_PIN, backward=MOTOR_BACKWARD_PIN)
enable_pin = PWMOutputDevice(MOTOR_ENABLE_PIN)
ir_sensor = DigitalInputDevice(IR_SENSOR_PIN, pull_up=True)  # active-low IR
white_led = LED(WHITE_LED_PIN)

speed = 0.2           # Motor speed (0.0 - 1.0)
motor_run_time = 0.1  # Time to pull bill in
required_denom = "50"  # Expected denomination (string must match YOLO label)

# --- Camera + YOLO ---
def capture_image():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Camera] Failed to open")
        return None
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None

def run_inference(model, frame, labels):
    resized = cv2.resize(frame, (480, 480))
    result = model.predict(resized, verbose=False)[0]
    if result.probs is None:
        return None, 0.0
    label_idx = int(result.probs.top1)
    return labels[label_idx], float(result.probs.top1conf)

def authenticate_bill(uv_model, uv_labels):
    print("[Auth] UV scan (turn UV light ON manually)...")
    frame = capture_image()
    if frame is None:
        return False
    label, conf = run_inference(uv_model, frame, uv_labels)
    print(f"[UV] {label} ({conf*100:.1f}%)")
    return conf >= 0.8 and label == "genuine"

def classify_denomination(denom_model, denom_labels):
    print("[Classify] White LED scan...")
    white_led.on()
    sleep(0.3)  # allow light to stabilize
    frame = capture_image()
    white_led.off()
    if frame is None:
        return None
    label, conf = run_inference(denom_model, frame, denom_labels)
    if conf < 0.8:
        return None
    print(f"[Denom] {label} ({conf*100:.1f}%)")
    return label

# --- Motor helpers ---
def motor_forward():
    enable_pin.value = speed
    motor.forward()
    print("[Motor] Forward")

def motor_reverse():
    enable_pin.value = speed
    motor.backward()
    print("[Motor] Reverse")

def motor_stop():
    motor.stop()
    enable_pin.off()
    print("[Motor] Stop")

# --- Main flow ---
def main():
    print("=== IR + Motor (PWM) + YOLO Test ===")

    # --- Load YOLO models ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    uv_model_path = os.path.join(script_dir, '..', 'models', "uv_cls_v2_ncnn_model")
    denom_model_path = os.path.join(script_dir, '..', 'models', "denom-cls-v2_ncnn_model")
    uv_model = YOLO(uv_model_path, task="classify")
    denom_model = YOLO(denom_model_path, task="classify")
    uv_labels = uv_model.names
    denom_labels = denom_model.names

    try:
        while True:
            if not ir_sensor.value:  # Active-low IR → bill detected
                print("[IR] Bill detected!")

                # Pull bill in
                motor_forward()
                sleep(motor_run_time)
                motor_stop()

                # UV authenticity
                if not authenticate_bill(uv_model, uv_labels):
                    print("[Result] ❌ Fake bill - rejecting...")
                    motor_reverse()
                    sleep(motor_run_time)
                    motor_stop()
                    continue

                # Denomination classification
                denom = classify_denomination(denom_model, denom_labels)
                if denom is None:
                    print("[Result] ❌ Could not classify denom - rejecting...")
                    motor_reverse()
                    sleep(motor_run_time)
                    motor_stop()
                    continue

                if denom != required_denom:
                    print(f"[Result] ❌ Wrong denom (expected {required_denom}, got {denom}) - rejecting...")
                    motor_reverse()
                    sleep(motor_run_time)
                    motor_stop()
                else:
                    print(f"[Result] ✅ Accepted ₱{denom}")
                    motor_stop()

                sleep(2)  # pause before next detection
            else:
                sleep(0.05)

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Stopping...")
    finally:
        motor_stop()
        white_led.off()

if __name__ == "__main__":
    main()
