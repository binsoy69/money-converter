import requests
import cv2

def capture_image():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Failed to access camera")
        return None

    ret, frame = cap.read()
    cap.release()

    if ret:
        return frame  # Return as NumPy array
    else:
        print("Failed to capture image")
        return None


API_URL = "https://yolo-docker.onrender.com/predict"  # replace with your Render URL


files = capture_image()
response = requests.post(API_URL, files=files)

if response.ok:
    result = response.json()
    print("Prediction:", result["class"])
    print("Confidence:", result["confidence"])
else:
    print("Error:", response.status_code, response.text)
