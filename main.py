import os
import cv2
from datetime import datetime, timedelta
import requests
from mega import Mega
from config import email, password , urlRtsp ,topic,folder

# RTSP stream URL
urlRtsp = urlRtsp
# Directory to save videos
pathSaveImg = "C:/Users/alron/PycharmProjects/"
# Camera ID
idc = "3"

# Initialize the video capture
vcap = cv2.VideoCapture(urlRtsp)
print("start**********************************************")
ret, frame1 = vcap.read()
ret, frame2 = vcap.read()
video_writer = None
motion_end_time = None
recording = False
record_duration_after_motion = timedelta(seconds=10)
current_video_file_path = None

def main():
    global vcap, ret, frame1, frame2, video_writer, motion_end_time, recording, current_video_file_path

    while vcap.isOpened():
        ftime = datetime.now()
        date_str = ftime.strftime("%d-%m-%Y")
        time_str = ftime.strftime("%H-%M-%S")
        dir_path = os.path.join(pathSaveImg, "cam" + idc, date_str)
        video_file_path = os.path.join(dir_path, time_str + ".avi")
        ret, frame2 = vcap.read()
        if ret:
            # Calculate the absolute difference between the current frame and the previous frame
            difference = cv2.absdiff(frame1, frame2)
            gray = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (27, 27), 0)
            _, threshold = cv2.threshold(blur, 27, 255, cv2.THRESH_BINARY)
            dilate = cv2.dilate(threshold, None, iterations=2)
            contours, _ = cv2.findContours(dilate, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            # Filter contours by size
            valid_contours = [c for c in contours if cv2.contourArea(c) > 500]

            if valid_contours:
                motion_end_time = datetime.now() + record_duration_after_motion
                if not recording:
                    recording = True

                    # Check if the directory exists, if not, create it
                    if not os.path.exists(dir_path):
                        try:
                            os.makedirs(dir_path)
                            print(f"Created directory: {dir_path}")
                        except OSError as e:
                            print(f"Error creating directory: {e}")

                    # Release the previous VideoWriter if it exists
                    if video_writer is not None:
                        video_writer.release()

                    # Define the codec and create VideoWriter object
                    fourcc = cv2.VideoWriter_fourcc(*"XVID")
                    video_writer = cv2.VideoWriter(video_file_path, fourcc, 20.0, (frame2.shape[1], frame2.shape[0]))
                    current_video_file_path = video_file_path
                    print(f"Started new video file: {video_file_path}")

            if recording:
                # Write the frame to the video file
                video_writer.write(frame2)
                if datetime.now() >= motion_end_time:
                    recording = False
                    if video_writer is not None:
                        video_writer.release()
                        video_writer = None

                    # Ensure the file exists before attempting to upload
                    if os.path.exists(current_video_file_path):
                        try:
                            mega = Mega()
                            mega.login(email, password)
                            Folder = mega.find(folder)
                            mega.upload(current_video_file_path, Folder[0])
                            r = requests.post(f"https://ntfy.sh/{topic}", data=f"Motion detected".encode(encoding='utf-8'))
                            r.raise_for_status()
                        except requests.exceptions.HTTPError as err:
                            print(f"HTTP error occurred: {err}")
                    else:
                        print(f"File not found for upload: {current_video_file_path}")
                    print("Stopped recording due to no movement for 10 seconds")

            # Display the output frame with contours
            cv2.drawContours(frame1, valid_contours, -1, (0, 0, 255), 2)
            cv2.imshow("image", frame1)

            # Move to the next frame
            frame1 = frame2
        else:
            # Restart the video capture if frame is not read correctly
            vcap.release()
            vcap = cv2.VideoCapture(urlRtsp)
            print("restart vcap")

        # Wait for 1 millisecond before reading the next frame
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release everything if job is finished
    if video_writer is not None:
        video_writer.release()
    vcap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
