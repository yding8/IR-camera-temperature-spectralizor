import cv2
from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np

class CameraThread(QThread):
    frameCaptured = pyqtSignal(np.ndarray)

    def __init__(self, app):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        self.running = False
        self.app = app

    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # 获取红框、绿框和蓝框的坐标和尺寸
                red_x, red_y, red_width, red_height = self.app.get_red_roi_geometry()
                green_x, green_y, green_width, green_height = self.app.get_green_roi_geometry()
                blue_x, blue_y, blue_width, blue_height = self.app.get_blue_roi_geometry()

                # 绘制红框、绿框和蓝框
                cv2.rectangle(frame, (red_x, red_y), (red_x + red_width, red_y + red_height), (0, 0, 255), 2)
                cv2.rectangle(frame, (green_x, green_y), (green_x + green_width, green_y + green_height), (52, 235, 143), 2)
                cv2.rectangle(frame, (blue_x, blue_y), (blue_x + blue_width, blue_y + blue_height), (255, 0, 0), 2)

                # 确保在录制状态时才写入视频
                if self.app.is_recording and self.app.video_writer is not None:
                    self.app.video_writer.write(frame)

                # 发射信号，更新帧
                self.frameCaptured.emit(frame)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

    def start(self):
        self.running = True
        super().start()

    def release_camera(self):
        self.cap.release()
