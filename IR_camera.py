import sys
import cv2
import numpy as np
import pandas as pd
import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QGridLayout, QFileDialog, QSlider, QGridLayout
from PyQt6.QtGui import QImage, QPixmap, QIcon
from PyQt6.QtCore import QThread, pyqtSignal, QTime, QSize, Qt, QRect, QDate

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from camera import CameraThread
from spectrum import SpectrumThread

class CameraApp(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("IR Camera Spectralization Software") 
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ND.ico")))

        # Initialize red, green, and blue ROI geometries
        self.red_roi_geometry = QRect(300, 150, 30, 30)
        self.green_roi_geometry = QRect(210, 210, 300, 30)
        self.blue_roi_geometry = QRect(150, 300, 30, 30)  # New blue ROI

        self.dragging = False
        self.is_spectrum_running = False
        self.drag_start_pos = None
        self.current_roi = None
        self.times = []
        self.red_intensities = []
        self.green_intensities = []
        self.blue_intensities = []  # New blue intensities
        self.is_recording = False
        self.video_writer = None

        self.initUI()

        self.camera_thread = CameraThread(self)
        self.camera_thread.frameCaptured.connect(self.update_image)

        self.spectrum_thread = SpectrumThread(self.camera_thread, self)
        self.spectrum_thread.spectrumCalculated.connect(self.update_plot)
        self.spectrum_thread.roiDrawn.connect(self.update_image_with_roi)

    def initUI(self):
        layout = QGridLayout()
        layout.setSpacing(15)  # 增加各组件之间的间距
        layout.setContentsMargins(20, 20, 20, 20)  # 设置整体边距

        # 按钮布局
        button_layout = QGridLayout()
        button_layout.setSpacing(10)  # 按钮之间的间距

        self.live_button = QPushButton('Live', self)
        self.live_button.clicked.connect(self.start_camera)
        self.acquire_button = QPushButton('Acquire', self)
        self.acquire_button.clicked.connect(self.start_spectrum_and_recording)
        self.stop_button = QPushButton('Stop', self)
        self.stop_button.clicked.connect(self.stop_camera_and_recording)
        self.save_button = QPushButton('Save', self)
        self.save_button.clicked.connect(self.save_spectrum)

        button_layout.addWidget(self.live_button, 0, 0, 1, 1)
        button_layout.addWidget(self.acquire_button, 0, 1, 1, 1)
        button_layout.addWidget(self.stop_button, 1, 0, 1, 1)
        button_layout.addWidget(self.save_button, 1, 1, 1, 1)

        layout.addLayout(button_layout, 0, 0, 1, 3)

        # 滑块和标签布局
        slider_layout = QGridLayout()
        slider_layout.setSpacing(10)  # 各滑块组之间的间距

        # 绿框滑块
        green_label = QLabel("Green Slider: Sample")
        self.green_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.green_width_slider.setRange(4, 640)
        self.green_width_slider.setValue(self.green_roi_geometry.width())
        self.green_width_slider.valueChanged.connect(self.update_green_width)
        self.green_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.green_height_slider.setRange(4, 480)
        self.green_height_slider.setValue(self.green_roi_geometry.height())
        self.green_height_slider.valueChanged.connect(self.update_green_height)

        slider_layout.addWidget(green_label, 0, 0, 1, 1)
        slider_layout.addWidget(self.green_width_slider, 1, 0, 1, 1)
        slider_layout.addWidget(self.green_height_slider, 2, 0, 1, 1)

        # 红框滑块
        red_label = QLabel("Red Slider: Hot Background")
        self.red_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.red_width_slider.setRange(4, 640)
        self.red_width_slider.setValue(self.red_roi_geometry.width())
        self.red_width_slider.valueChanged.connect(self.update_red_width)
        self.red_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.red_height_slider.setRange(4, 480)
        self.red_height_slider.setValue(self.red_roi_geometry.height())
        self.red_height_slider.valueChanged.connect(self.update_red_height)

        slider_layout.addWidget(red_label, 0, 1, 1, 1)
        slider_layout.addWidget(self.red_width_slider, 1, 1, 1, 1)
        slider_layout.addWidget(self.red_height_slider, 2, 1, 1, 1)

        # 蓝框滑块
        blue_label = QLabel("Blue Slider: Cold Background")
        self.blue_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.blue_width_slider.setRange(4, 640)
        self.blue_width_slider.setValue(self.blue_roi_geometry.width())
        self.blue_width_slider.valueChanged.connect(self.update_blue_width)
        self.blue_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.blue_height_slider.setRange(4, 480)
        self.blue_height_slider.setValue(self.blue_roi_geometry.height())
        self.blue_height_slider.valueChanged.connect(self.update_blue_height)

        slider_layout.addWidget(blue_label, 0, 2, 1, 1)
        slider_layout.addWidget(self.blue_width_slider, 1, 2, 1, 1)
        slider_layout.addWidget(self.blue_height_slider, 2, 2, 1, 1)

        layout.addLayout(slider_layout, 5, 0, 1, 3)

        # 视频显示区域（640x480）
        self.image_label = QLabel(self)
        self.image_label.setFixedSize(QSize(640, 480))
        self.set_noise_background()
        self.image_label.setStyleSheet("border: 1px solid black;")
        layout.addWidget(self.image_label, 1, 0, 4, 3)

        # 光谱显示区域
        spec_layout = QGridLayout()
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Summary")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Intensity")
        spec_layout.addWidget(self.canvas, 0, 0, 1, 1)

        # 各区域光谱显示
        self.green_canvas = FigureCanvas(Figure())
        self.green_ax = self.green_canvas.figure.add_subplot(111)
        self.green_ax.set_title("Sample ROI")
        self.green_ax.set_xlabel("Time (s)")
        self.green_ax.set_ylabel("Intensity")
        spec_layout.addWidget(self.green_canvas, 0, 1, 1, 1)

        self.red_canvas = FigureCanvas(Figure())
        self.red_ax = self.red_canvas.figure.add_subplot(111)
        self.red_ax.set_title("Red Hot Background ROI")
        self.red_ax.set_xlabel("Time (s)")
        self.red_ax.set_ylabel("Intensity")
        spec_layout.addWidget(self.red_canvas, 1, 0, 1, 1)

        self.blue_canvas = FigureCanvas(Figure())
        self.blue_ax = self.blue_canvas.figure.add_subplot(111)
        self.blue_ax.set_title("Blue Cold Background ROI")
        self.blue_ax.set_xlabel("Time (s)")
        self.blue_ax.set_ylabel("Intensity")
        spec_layout.addWidget(self.blue_canvas, 1, 1, 1, 1)

        layout.addLayout(spec_layout, 0, 5, 6, 5)

        self.setLayout(layout)
        self.resize(1650, 1000)  # 适合内容的大小

    def center(self):
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        x = (screen_geometry.width() - window_geometry.width()) // 6
        #y = (screen_geometry.height() + window_geometry.height()) // 2
        self.move(x , 10)

    def set_noise_background(self):
        noise = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        h, w, ch = noise.shape
        bytes_per_line = ch * w
        qimg = QImage(noise.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        self.image_label.setPixmap(QPixmap.fromImage(qimg))

    def update_image(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        self.image_label.setPixmap(QPixmap.fromImage(qimg))

    def update_image_with_roi(self, frame):
        self.update_image(frame)

    def update_plot(self, current_time, red_intensity, green_intensity, blue_intensity):
    # 添加蓝色框的平均强度显示
        self.times.append(current_time)
        self.red_intensities.append(red_intensity)
        self.green_intensities.append(green_intensity)
        self.blue_intensities.append(blue_intensity)
    
    # 更新主光谱显示
        self.ax.clear()
        self.ax.plot(self.times, self.red_intensities, 'r-', label="Red ROI")
        self.ax.plot(self.times, self.green_intensities, 'g-', label="Green ROI")
        self.ax.plot(self.times, self.blue_intensities, 'b-', label="Blue ROI")
        self.ax.legend()
        self.ax.set_title("Time - Red, Green, and Blue Average Intensity")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Intensity")
        self.canvas.draw()
    
    # 更新红框光谱显示
        self.red_ax.clear()
        self.red_ax.plot(self.times, self.red_intensities, 'r-', linewidth=2)
        self.red_ax.set_xlabel("Time (s)")
        self.red_ax.set_ylabel("Intensity")
        self.red_canvas.draw()

    # 更新绿框光谱显示
        self.green_ax.clear()
        self.green_ax.plot(self.times, self.green_intensities, 'g-', linewidth=2)
        self.green_ax.set_xlabel("Time (s)")
        self.green_ax.set_ylabel("Intensity")
        self.green_canvas.draw()

    # 更新蓝框光谱显示
        self.blue_ax.clear()
        self.blue_ax.plot(self.times, self.blue_intensities, 'b-', linewidth=2)
        self.blue_ax.set_xlabel("Time (s)")
        self.blue_ax.set_ylabel("Intensity")
        self.blue_canvas.draw()

    def update_blue_width(self, value):
        self.blue_roi_geometry.setWidth(value)
        self.enforce_bounds(self.blue_roi_geometry)
        self.update()

    def update_blue_height(self, value):
        self.blue_roi_geometry.setHeight(value)
        self.enforce_bounds(self.blue_roi_geometry)
        self.update()

    def get_blue_roi_geometry(self):
        return self.blue_roi_geometry.x(), self.blue_roi_geometry.y(), self.blue_roi_geometry.width(), self.blue_roi_geometry.height()

    def save_spectrum(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Spectrum Data", "", "CSV Files (*.csv);;All Files (*)")
        if file_name:
            spectrum_data = pd.DataFrame({
                "Time (s)": self.times,
                "Green_sample": self.green_intensities,
                "Red_Hot": self.red_intensities,
                "Blue_Cold": self.blue_intensities
            })
            spectrum_data.to_csv(file_name, index=False)
            print(f"Spectrum data saved as {file_name}")

    def start_camera(self):
        self.camera_thread.start()

    def stop_camera_and_recording(self):
        self.camera_thread.stop()
        self.stop_spectrum()

        if self.is_recording:
            self.is_recording = False
            self.video_writer.release()
            self.date = QDate.currentDate().toString("yyyy_MM_dd")
            self.time = QTime.currentTime().toString("hh_mm")
            #videos_path = os.path.join(os.path.expanduser('~'), 'Videos', self.date + '_' + self.time + '_' + 'recorded_video.avi')
            videos_path = os.path.join('E:','Kuno.LaserCooling', 'Video', self.date + '_' + self.time + '_' + 'recorded_video.avi')
            print(f"Video saved to: {videos_path}")

    def start_spectrum_and_recording(self):
        self.times.clear()
        self.red_intensities.clear()
        self.green_intensities.clear()
        self.blue_intensities.clear()
        self.is_spectrum_running = True

        self.is_recording = True
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.date = QDate.currentDate().toString("yyyy_MM_dd")
        self.time = QTime.currentTime().toString("hh_mm")
        #videos_path = os.path.join(os.path.expanduser('~'), 'Videos', self.date + '_' + self.time + '_' + 'recorded_video.avi')
        videos_path = os.path.join('E:','Kuno.LaserCooling', 'Video', self.date + '_' + self.time + '_' + 'recorded_video.avi')
        self.video_writer = cv2.VideoWriter(videos_path, fourcc, 20.0, (640, 480))

        self.camera_thread.start()
        self.spectrum_thread.start()

    def stop_spectrum(self):
        self.is_spectrum_running = False
        self.red_width_slider.setDisabled(False)
        self.red_height_slider.setDisabled(False)
        self.green_width_slider.setDisabled(False)
        self.green_height_slider.setDisabled(False)
        self.spectrum_thread.stop()

    def mousePressEvent(self, event):
        if not self.is_spectrum_running:
            # 定义最小可点击区域为 100x100
            red_click_area = QRect(self.red_roi_geometry.x()-10, self.red_roi_geometry.y(), max(100, self.red_roi_geometry.width()), max(300, self.red_roi_geometry.height()))
            green_click_area = QRect(self.green_roi_geometry.x(), self.green_roi_geometry.y(), max(300, self.green_roi_geometry.width()), max(300, self.green_roi_geometry.height()))
            blue_click_area = QRect(self.blue_roi_geometry.x(), self.blue_roi_geometry.y(), max(300, self.blue_roi_geometry.width()), max(300, self.blue_roi_geometry.height()))

            # 处理红框
            if red_click_area.contains(event.pos()):
                self.dragging = True
                self.drag_start_pos = event.pos() - self.red_roi_geometry.topLeft()
                self.current_roi = self.red_roi_geometry
            # 处理绿框
            elif green_click_area.contains(event.pos()):
                self.dragging = True
                self.drag_start_pos = event.pos() - self.green_roi_geometry.topLeft()
                self.current_roi = self.green_roi_geometry
            # 处理蓝框
            elif blue_click_area.contains(event.pos()):
                self.dragging = True
                self.drag_start_pos = event.pos() - self.blue_roi_geometry.topLeft()
                self.current_roi = self.blue_roi_geometry

    def mouseMoveEvent(self, event):
        if self.dragging and self.current_roi:
            new_top_left = event.pos() - self.drag_start_pos
            self.current_roi.moveTopLeft(new_top_left)
            self.enforce_bounds(self.current_roi)
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def update_red_width(self, value):
        self.red_roi_geometry.setWidth(value)
        self.enforce_bounds(self.red_roi_geometry)
        self.update()

    def update_red_height(self, value):
        self.red_roi_geometry.setHeight(value)
        self.enforce_bounds(self.red_roi_geometry)
        self.update()

    def update_green_width(self, value):
        self.green_roi_geometry.setWidth(value)
        self.enforce_bounds(self.green_roi_geometry)
        self.update()

    def update_green_height(self, value):
        self.green_roi_geometry.setHeight(value)
        self.enforce_bounds(self.green_roi_geometry)
        self.update()

    def enforce_bounds(self, roi_geometry):
        if roi_geometry.right() > 640:
            roi_geometry.moveRight(640)
        if roi_geometry.bottom() > 480:
            roi_geometry.moveBottom(480)
        if roi_geometry.left() < 0:
            roi_geometry.moveLeft(0)
        if roi_geometry.top() < 0:
            roi_geometry.moveTop(0)

    def get_red_roi_geometry(self):
        return self.red_roi_geometry.x(), self.red_roi_geometry.y(), self.red_roi_geometry.width(), self.red_roi_geometry.height()

    def get_green_roi_geometry(self):
        return self.green_roi_geometry.x(), self.green_roi_geometry.y(), self.green_roi_geometry.width(), self.green_roi_geometry.height()

    def closeEvent(self, event):
        self.camera_thread.stop()
        self.camera_thread.release_camera()
        self.spectrum_thread.stop()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CameraApp()
    ex.show()
    sys.exit(app.exec())
