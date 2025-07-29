import counter
import streamer
import threading

# Start the Flask app in a separate thread
flask_thread = threading.Thread(target=streamer.run_app)
flask_thread.daemon = True
flask_thread.start()

beesIn, beesOut = counter.countBees('./videos/314.mp4', display_video=True)
counter.report_telemetry_async(beesIn, beesOut)
