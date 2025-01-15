import cv2
import threading
import time
from pathlib import Path
from tkinter import Tk, Canvas, Button, PhotoImage, filedialog, messagebox, Label
from PIL import Image, ImageTk
import pyttsx3
import pandas as pd

# Initialize pyttsx3 for text-to-speech
engine = pyttsx3.init()

# Flag to control the video capture loop
video_running = False
audio_lock = threading.Lock()  # Prevent overlapping audio

# Load the CSV file for color mapping
try:
    csv = pd.read_csv("colors.csv", names=["id", "color_name", "hex", "R", "G", "B"])
    csv["R"] = pd.to_numeric(csv["R"], errors="coerce").fillna(0).astype(int)
    csv["G"] = pd.to_numeric(csv["G"], errors="coerce").fillna(0).astype(int)
    csv["B"] = pd.to_numeric(csv["B"], errors="coerce").fillna(0).astype(int)
except FileNotFoundError:
    print("Error: 'colors.csv' file not found. Ensure it is in the same directory as this script.")
    csv = pd.DataFrame(columns=["id", "color_name", "hex", "R", "G", "B"])

# Function to get the closest color name from RGB values
def getColorName(R, G, B):
    minimum = float("inf")
    cname = "Unknown"
    for i in range(len(csv)):
        try:
            d = abs(R - csv.loc[i, "R"]) + abs(G - csv.loc[i, "G"]) + abs(B - csv.loc[i, "B"])
            if d < minimum:
                minimum = d
                cname = csv.loc[i, "color_name"]
        except ValueError:
            continue  # Skip rows with invalid data
    return cname

# Function to recognize the color from the BGR format
def detect_color(bgr):
    b, g, r = bgr
    return getColorName(r, g, b)

# Function to convert OpenCV image to Tkinter format
def cv_to_tk(cv_image):
    color_converted = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(color_converted)
    return ImageTk.PhotoImage(image)

# Function to capture video and detect colors
def capture_video(label, text_label):
    global video_running
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        messagebox.showerror("Error", "Unable to access the camera. Please check your device.")
        return

    last_spoken_time = 0  # Timestamp for the last spoken color
    speak_interval = 3.0  # Time interval in seconds

    while video_running:
        ret, frame = cap.read()
        if not ret:
            break

        height, width, _ = frame.shape
        center_x, center_y = width // 2, height // 2

        # Highlight the center area
        cv2.rectangle(frame, (center_x - 50, center_y - 50), (center_x + 50, center_y + 50), (0, 255, 0), 2)
        center_pixel = frame[center_y, center_x]
        detected_color = detect_color(center_pixel)

        # Update the GUI label
        frame_tk = cv_to_tk(frame)
        label.config(image=frame_tk)
        label.image = frame_tk

        # Speak and display detected color at a controlled interval
        current_time = time.time()
        if current_time - last_spoken_time >= speak_interval:
            spoken_text = f"Detected color is {detected_color}"
            with audio_lock:
                engine.say(spoken_text)
                engine.runAndWait()
            text_label.config(text=spoken_text)
            last_spoken_time = current_time

    cap.release()

# Function to start video capture in a separate thread
def start_video(label, text_label):
    global video_running
    video_running = True
    video_thread = threading.Thread(target=capture_video, args=(label, text_label))
    video_thread.start()

# Function to stop the video capture and reset the video label background
def stop_video(label):
    global video_running
    video_running = False
    # Reset the video label to match the background
    label.config(image="", bg="#3E3688")

# Function to handle image upload and color detection
def upload_image(label, text_label):
    global video_running
    stop_video(label)  # Stop the video and reset the display

    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.jpg;*.jpeg;*.png;*.bmp")])
    if not file_path:
        # Resume video if no file is selected
        video_running = True
        threading.Thread(target=capture_video, args=(label, text_label)).start()
        return

    # Load and process the uploaded image
    image = cv2.imread(file_path)
    if image is None:
        messagebox.showerror("Error", "Unable to load the image.")
        return

    # Detect color at the center
    height, width, _ = image.shape
    center_x, center_y = width // 2, height // 2

    # Add a square frame at the center
    square_size = 100  # Size of the square
    top_left = (center_x - square_size // 2, center_y - square_size // 2)
    bottom_right = (center_x + square_size // 2, center_y + square_size // 2)
    cv2.rectangle(image, top_left, bottom_right, (0, 255, 0), 2)

    # Get the color of the center pixel
    center_pixel = image[center_y, center_x]
    detected_color = detect_color(center_pixel)

    # Convert the image to Tkinter format
    frame_tk = cv_to_tk(image)
    label.config(image=frame_tk)
    label.image = frame_tk

    # Speak and display detected color
    spoken_text = f"Detected color is {detected_color}"
    with audio_lock:
        engine.say(spoken_text)
        engine.runAndWait()
    text_label.config(text=spoken_text)

# GUI setup
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"pic")

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

def start_gui():
    window = Tk()

    # Get screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Set the window width and height
    window_width = 846
    window_height = 762
    # Calculate the position to center the window
    position_top = (screen_height // 2) - (window_height // 2)
    position_left = (screen_width // 2) - (window_width // 2)

    # Set the position of the window
    window.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")

    canvas = Canvas(
        window,
        bg="#3E3688",
        height=762,
        width=846,
        bd=0,
        highlightthickness=0,
        relief="ridge"
    )
    canvas.place(x=0, y=0)

    # Display the image at the top
    image_image_1 = PhotoImage(file=relative_to_assets("image_1.png"))
    canvas.create_image(434.0, 57.0, image=image_image_1)

    # Label to display video or uploaded image
    video_label = Label(window, bg="#3E3688", relief="solid", borderwidth=2)
    video_label.place(x=100, y=90, width=640, height=480)

    # Label to display spoken text
    text_label = Label(window, bg="#3E3688", fg="white", font=("Arial Black", 20), wraplength=800, anchor="center")
    text_label.place(x=100, y=690, width=640, height=40)

    # Buttons to control functionalities
    button_image_1 = PhotoImage(file=relative_to_assets("button_1.png"))
    Button(
        image=button_image_1,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: start_video(video_label, text_label),
        relief="flat"
    ).place(x=75.0, y=587.0, width=238.0, height=71.0)

    button_image_2 = PhotoImage(file=relative_to_assets("button_2.png"))
    Button(
        image=button_image_2,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: upload_image(video_label, text_label),
        relief="flat"
    ).place(x=336.0, y=587.0, width=238.0, height=71.0)

    button_image_3 = PhotoImage(file=relative_to_assets("button_3.png"))
    Button(
        image=button_image_3,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: stop_video(video_label),
        relief="flat"
    ).place(x=596.0, y=587.0, width=193.0, height=71.0)

    window.resizable(False, False)
    window.mainloop()

if __name__ == "__main__":
    start_gui()
