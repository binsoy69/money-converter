import os
import sys
import cv2
import numpy as np
from ultralytics import YOLO

# Load YOLO classification model
# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Build the absolute path to the model
model_path = os.path.join(script_dir, '..', 'models', 'denom-cls-v2_ncnn_model')

if not os.path.exists(model_path):
    print(f"Model file not found at: {model_path}")
    sys.exit()

model = YOLO(model_path, task='classify')

# Access the class labels
labels = model.names  # For example, {0: 'fake', 1: 'real'}

# Start video capture
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    sys.exit()

print("Press 'P' to take a picture and classify it.")
print("Press 'Q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        break

    # Show the current video frame
    cv2.imshow("Live Feed - Press 'P' to Predict", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('p') or key == ord('P'):
        # Resize the frame if needed (YOLOv8 classifier usually accepts 224x224)
        resized_frame = cv2.resize(frame, (480, 480))

        # Run prediction
        results = model.predict(resized_frame, verbose=False)
        pred = results[0]
        
        # Get predicted class index and confidence
        class_id = int(pred.probs.top1)
        confidence = float(pred.probs.top1conf)
        label = labels[class_id]

        # Display result
        print(f"Prediction: {label} ({confidence * 100:.2f}%)")
        cv2.putText(frame, f"{label} ({confidence * 100:.2f}%)", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow("Prediction Result", frame)
        cv2.waitKey(2000)  # Display for 2 seconds

    elif key == ord('q') or key == ord('Q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()

