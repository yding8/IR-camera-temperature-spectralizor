import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QTime
import numpy as np

class SpectrumThread(QThread):
    # 增加蓝框的强度值作为信号参数
    spectrumCalculated = pyqtSignal(float, float, float, float)  # 包括 red, green 和 blue 的强度值
    roiDrawn = pyqtSignal(object)

    def __init__(self, camera_thread, app):
        super().__init__()
        self.camera_thread = camera_thread
        self.running = False
        self.frame_counter = 0
        self.start_time = None
        self.app = app

    def run(self):
        while self.running:
            ret, frame = self.camera_thread.cap.read()
            if ret:
                self.frame_counter += 1
                
                # 获取红、绿和蓝框的几何信息
                red_x, red_y, red_width, red_height = self.app.get_red_roi_geometry()
                green_x, green_y, green_width, green_height = self.app.get_green_roi_geometry()
                blue_x, blue_y, blue_width, blue_height = self.app.get_blue_roi_geometry()

                # 绘制红、绿和蓝框
                self.draw_roi(frame, red_x, red_y, red_width, red_height, color=(0, 0, 255))
                self.draw_roi(frame, green_x, green_y, green_width, green_height, color=(0, 255, 0))
                self.draw_roi(frame, blue_x, blue_y, blue_width, blue_height, color=(255, 0, 0))
                
                # 发出绘制后的帧
                self.roiDrawn.emit(frame)

                if self.frame_counter % 15 == 0:
                    # 计算每个框的平均强度
                    red_roi = frame[red_y:red_y + red_height, red_x:red_x + red_width]
                    green_roi = frame[green_y:green_y + green_height, green_x:green_x + green_width]
                    blue_roi = frame[blue_y:blue_y + blue_height, blue_x:blue_x + blue_width]

                    red_avg_intensity = np.mean(red_roi)
                    green_avg_intensity = np.mean(green_roi)
                    blue_avg_intensity = np.mean(blue_roi)

                    # 计算当前时间
                    current_time = (QTime.currentTime().msecsSinceStartOfDay() - self.start_time) / 1000.0

                    # 发出信号，包括时间、红、绿、蓝的平均强度
                    self.spectrumCalculated.emit(current_time, red_avg_intensity, green_avg_intensity, blue_avg_intensity)

    def draw_roi(self, frame, x, y, width, height, color):
        cv2.rectangle(frame, (x, y), (x + width, y + height), color, 2)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

    def start(self):
        self.start_time = QTime.currentTime().msecsSinceStartOfDay()
        self.running = True
        super().start()
