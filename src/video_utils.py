import cv2
import platform
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject

class GStreamerWriter:
    def __init__(self, output_file, fps, resolution):
        Gst.init(None)
        self.output_file = output_file
        width, height = resolution
        self.fps = fps
        self.frame_count = 0
        self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
        
        pipeline_desc = (
            f"appsrc name=source is-live=true block=true format=GST_FORMAT_TIME "
            f"caps=video/x-raw,format=BGR,width={width},height={height},framerate={int(fps)}/1 ! "
            f"videoconvert ! "
            f"video/x-raw,format=I420 ! "
            f"x264enc speed-preset=ultrafast tune=zerolatency ! "
            f"h264parse ! "
            f"mp4mux ! "
            f"filesink location={self.output_file} "
        )
        
        self.pipeline = Gst.parse_launch(pipeline_desc)
        if self.pipeline is None:
            raise Exception("Failed to parse GStreamer pipeline.")
            
        self.appsrc = self.pipeline.get_by_name('source')
        self.pipeline.set_state(Gst.State.PLAYING)

    def write(self, frame):
        data = frame.tobytes()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        
        buf.pts = self.frame_count * self.duration
        buf.duration = self.duration
        self.frame_count += 1
        
        self.appsrc.emit('push-buffer', buf)

    def release(self):
        self.appsrc.emit('end-of-stream')
        bus = self.pipeline.get_bus()
        bus.poll(Gst.MessageType.EOS, Gst.CLOCK_TIME_NONE)
        self.pipeline.set_state(Gst.State.NULL)

    def isOpened(self):
        return self.pipeline is not None

class VideoWriterFactory:
    """
    A factory for creating cv2.VideoWriter objects.
    It remembers the last successful codec to avoid repeated fallbacks.
    """
    _preferred_codec = 'avc1'

    @classmethod
    def create_writer(cls, output_path, fps, resolution):
        """
        Creates a cv2.VideoWriter object using the preferred codec.
        If the preferred codec fails, it tries a fallback and updates the preference.
        """
        if platform.system() == 'Linux':
            try:
                return GStreamerWriter(output_path, fps, resolution)
            except ImportError:
                print("⚠️ GStreamer not available, falling back to OpenCV's VideoWriter.")
            except Exception as e:
                print(f"❌ Failed to initialize GStreamer: {e}")
                print("Falling back to OpenCV's VideoWriter.")

        width, height = resolution
        
        # Try the preferred codec first
        fourcc = cv2.VideoWriter_fourcc(*cls._preferred_codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if writer.isOpened():
            return writer
            
        # If the preferred codec failed and it was the default 'avc1', try the fallback
        if cls._preferred_codec == 'avc1':
            print("⚠️ Failed to open VideoWriter with 'avc1' codec, trying 'mp4v'...")
            fallback_codec = 'mp4v'
            fourcc = cv2.VideoWriter_fourcc(*fallback_codec)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if writer.isOpened():
                print(f"✅ Fallback codec '{fallback_codec}' succeeded. Setting as preferred.")
                cls._preferred_codec = fallback_codec
                return writer

        # If we've reached here, all attempts have failed
        print(f"❌ Failed to open VideoWriter for {output_path} with any available codec.")
        return None
