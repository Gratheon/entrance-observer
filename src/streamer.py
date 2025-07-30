from flask import Flask, Response
import cv2

app = Flask(__name__)
video_frame = None

def generate_frames():
    global video_frame
    while True:
        if video_frame is not None:
            (flag, encodedImage) = cv2.imencode(".jpg", video_frame)
            if not flag:
                continue
            yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                  bytearray(encodedImage) + b'\r\n')

@app.route("/")
def video_feed():
    return Response(generate_frames(),
                    mimetype = "multipart/x-mixed-replace; boundary=frame")

def run_app():
    app.run(host='0.0.0.0', port=8080, debug=True, threaded=True, use_reloader=False)
