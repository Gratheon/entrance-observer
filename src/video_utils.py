import cv2
import platform

class OpenCVWriterWrapper:
    def __init__(self, writer):
        self.writer = writer

    def write(self, frame, capture_time_monotonic=None):
        # The timestamp is ignored, but the method signature is compatible
        self.writer.write(frame)

    def release(self):
        self.writer.release()

    def isOpened(self):
        return self.writer.isOpened()

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
        width, height = resolution
        
        # Try the preferred codec first
        fourcc = cv2.VideoWriter_fourcc(*cls._preferred_codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if writer.isOpened():
            return OpenCVWriterWrapper(writer)
            
        # If the preferred codec failed and it was the default 'avc1', try the fallback
        if cls._preferred_codec == 'avc1':
            print("⚠️ Failed to open VideoWriter with 'avc1' codec, trying 'mp4v'...")
            fallback_codec = 'mp4v'
            fourcc = cv2.VideoWriter_fourcc(*fallback_codec)
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if writer.isOpened():
                print(f"✅ Fallback codec '{fallback_codec}' succeeded. Setting as preferred.")
                cls._preferred_codec = fallback_codec
                return OpenCVWriterWrapper(writer)

        # If we've reached here, all attempts have failed
        print(f"❌ Failed to open VideoWriter for {output_path} with any available codec.")
        return None
