# tests/test_ir_motor_yolo.py
import time
import os
import cv2
import RPi.GPIO as GPIO
from ultralytics import YOLO

# --- Pin configuration (adjust to your wiring) ---
IR_PIN = 17          # IR sensor (active-low)
MOTOR_IN1 = 22       # Motor driver input 1
MOTOR_IN2 = 27       # Motor driver input 2
WHITE_LED_PIN = 23   # White LED pin

# --- Setup GPIO ---
def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(IR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(MOTOR_IN1, GPIO.OUT)
    GPIO.setup(MOTOR_IN2, GPIO.OUT)
    GPIO.setup(WHITE_LED_PIN, GPIO.OUT)
    GPIO.output(WHITE_LED_PIN, GPIO.LOW)

def motor_forward():
    GPIO.output(MOTOR_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_IN2, GPIO.LOW)
    print("[Motor] Forward")

def motor_reverse():
    GPIO.output(MOTOR_IN1, GPIO.LOW)
    GPIO.output(MOTOR_IN2, GPIO.HIGH)
    print("[Motor] Reverse")

def motor_stop():
    GPIO.output(MOTOR_IN1, GPIO.LOW)
    GPIO.output(MOTOR_IN2, GPIO.LOW)
    print("[Motor] Stop")

def led_on():
    GPIO.output(WHITE_LED_PIN, GPIO.HIGH)

def led_off():
    GPIO.output(WHITE_LED_PIN, GPIO.LOW)

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
    print("[Auth] UV scan...")
    frame = capture_image()
    if frame is None:
        return False
    label, conf = run_inference(uv_model, frame, uv_labels)
    print(f"[UV] {label} ({conf*100:.1f}%)")
    return conf >= 0.8 and label == "genuine"

def classify_denomination(denom_model, denom_labels):
    print("[Classify] White LED scan...")
    led_on()
    time.sleep(0.3)  # allow light to stabilize
    frame = capture_image()
    led_off()
    if frame is None:
        return None
    label, conf = run_inference(denom_model, frame, denom_labels)
    if conf < 0.8:
        return None
    print(f"[Denom] {label} ({conf*100:.1f}%)")
    return label

# --- Main test flow ---
def main():
    setup_gpio()
    print("=== IR Sensor + Motor + YOLO Test ===")

    # --- Load models ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    uv_model_path = os.path.join(script_dir, '..', 'models', "uv_cls_v2_ncnn_model")
    denom_model_path = os.path.join(script_dir, '..', 'models', "denom-cls-v2_ncnn_model")
    uv_model = YOLO(uv_model_path, task="classify")
    denom_model = YOLO(denom_model_path, task="classify")
    uv_labels = uv_model.names
    denom_labels = denom_model.names

    required = "100"  # expected denomination as string (e.g., "20", "50", "100")

    try:
        while True:
            if GPIO.input(IR_PIN) == GPIO.LOW:  # bill detected
                print("[IR] Bill detected, running motor...")
                motor_forward()
                time.sleep(2)  # pull bill in
                motor_stop()

                # --- Authenticate under UV ---
                if not authenticate_bill(uv_model, uv_labels):
                    print("[Result] ❌ Fake bill detected, rejecting...")
                    motor_reverse()
                    time.sleep(2)
                    motor_stop()
                    time.sleep(1)
                    continue

                # --- Classify denomination under white LED ---
                denom = classify_denomination(denom_model, denom_labels)
                if denom is None:
                    print("[Result] ❌ Unable to classify denomination, rejecting...")
                    motor_reverse()
                    time.sleep(2)
                    motor_stop()
                    time.sleep(1)
                    continue

                if denom != required:
                    print(f"[Result] ❌ Wrong denom (expected {required}, got {denom}), rejecting...")
                    motor_reverse()
                    time.sleep(2)
                    motor_stop()
                else:
                    print(f"[Result] ✅ Accepted ₱{denom}")
                    motor_stop()

                time.sleep(2)  # pause before next detection
            else:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nExiting test...")
    finally:
        motor_stop()
        led_off()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
