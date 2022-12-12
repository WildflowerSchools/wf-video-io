import cv2


class VideoReader:
    def __init__(self, video_path):
        self.video_path = video_path
        self.video = cv2.VideoCapture(self.video_path)

    def __del__(self):
        self.video.release()

    def frames(self):
        return self.video.get(cv2.CAP_PROP_FRAME_COUNT)

    def fps(self):
        return self.video.get(cv2.CAP_PROP_FPS)

    def duration(self):
        return self.frames() / self.fps()

    def width(self):
        return self.video.get(cv2.CAP_PROP_FRAME_WIDTH)

    def height(self):
        return self.video.get(cv2.CAP_PROP_FRAME_HEIGHT)
