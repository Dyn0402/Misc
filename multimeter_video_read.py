import cv2
import pytesseract
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np

# Set up Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Set path to Tesseract executable

# Load pretrained model from TensorFlow Hub
model_url = "https://tfhub.dev/google/imagenet/mobilenet_v2_100_224/classification/4"
model = hub.KerasLayer(model_url, input_shape=(224, 224, 3))

# Set up video capture
cap = cv2.VideoCapture('C:/Users/Dylan/Downloads/current_video.mp4')

# Define ROI coordinates
x, y, w, h = 250, 300, 600, 450

# Read first frame to get dimensions
ret, frame = cap.read()
height, width, _ = frame.shape

# Set up text detector
config = ('-l eng --oem 1 --psm 3')
text_detector = pytesseract.image_to_string

# Loop through frames
while (cap.isOpened()):
    # Read frame
    ret, frame = cap.read()

    # If end of video, break out of loop
    if not ret:
        break

    # Crop to ROI
    roi = frame[y:y + h, x:x + w]

    # Convert ROI to grayscale
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # Threshold to remove noise
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    digits = pytesseract.image_to_string(thresh)
    #Print digit string and frame timestamp
    print(f"{digits} at {cap.get(cv2.CAP_PROP_POS_MSEC)}ms")

    # # Find contours
    # contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    #
    # # Loop through contours
    # for cnt in contours:
    #     # Get bounding box
    #     x_cnt, y_cnt, w_cnt, h_cnt = cv2.boundingRect(cnt)
    #
    #     # Extract digit
    #     digit = gray[y_cnt:y_cnt + h_cnt, x_cnt:x_cnt + w_cnt]
    #
    #     # Check if digit is large enough
    #     if digit.shape[0] < 10 or digit.shape[1] < 10:
    #         continue
    #
    #     # Resize digit to match Tesseract's input size
    #     digit = cv2.resize(digit, (100, 100))
    #
    #     # Convert digit to string using Tesseract
    #     digit_string = text_detector(digit, config=config)
    #
    #     # Print digit string and frame timestamp
    #     print(f"{digit_string.strip()} at {cap.get(cv2.CAP_PROP_POS_MSEC)}ms")
    #
    #     # Draw bounding box around digit
    #     cv2.rectangle(roi, (x_cnt, y_cnt), (x_cnt + w_cnt, y_cnt + h_cnt), (0, 0, 255), 2)
    #     cv2.rectangle(thresh, (x_cnt, y_cnt), (x_cnt + w_cnt, y_cnt + h_cnt), (0, 0, 255), 2)

    # Display frame
    cv2.imshow('frame', thresh)
    # cv2.imshow('frame', roi)

    # Quit if 'q' key is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
