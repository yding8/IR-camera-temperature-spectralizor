import sys
import serial
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt

# Serial port settings
port = 'COM3'  # Modify according to your actual port
baudrate = 115200
timeout = 1
ser = serial.Serial(port, baudrate, timeout=timeout)



# Define a function to send commands
def send_command(command_data):
    """
    Send command with given data and calculate the full packet.
    Data format: [device_address, class_address, subclass_address, rw_flag, data]
    """
    begin = 0xF0
    end = 0xFF
    size = len(command_data)  # N + 4, plus 1 byte for CHK
    size_byte = size.to_bytes(1, byteorder='big')
    
    # Calculate CHK Take the lower 8 bits
    chk = sum(command_data)& 0xFF
    
    # Full command packet
    full_command = bytearray([begin]) + size_byte + bytearray(command_data) + bytearray([chk, end])
    
    if ser.is_open:
        ser.write(full_command)
        print("Command sent:", ' '.join(f'{byte:02X}' for byte in full_command))
        #time.sleep(0.1)
        
        # Read response
        response = ser.read(10)  # Adjust response length if necessary
        if response:
            print("Response (Hex):", ' '.join(f'{byte:02X}' for byte in response))
            return response
        else:
            print("No response received.")
            return None
    else:
        print("Serial port not open")
        return None

# Define camera control functions
def set_shutter_mode(mode):
    """
    设置相机的自动快门控制模式。
    
    参数:
        mode (int): 快门模式 (0x00到0x03)
            0x00: 自动控制关闭
            0x01: 自动切换，时间控制
            0x02: 自动切换，温差控制
            0x03: 全自动控制 (默认)
    """
    command = bytearray([0x36, 0x7C, 0x04, 0x00, mode])
    send_command(command)

def set_brightness(brightness):
    """
    Set the brightness of the camera.
    Brightness value (0~100)
    """
    brightness_hex = brightness.to_bytes(1, byteorder='big')
    command = [0x36, 0x78, 0x02, 0x00] + list(brightness_hex)
    response = send_command(command)

def set_contrast(contrast):
    """
    Set the contrast of the camera.
    contrast value (0~100)
    """
    contrast_hex = contrast.to_bytes(1, byteorder='big')
    command = [0x36, 0x78, 0x03, 0x00] + list(contrast_hex)
    send_command(command)

def save_current_settings():
    command = bytearray([0x36, 0x74, 0x10, 0x00, 0x00])
    send_command(command)

# GUI Application
class CameraControlApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Camera Control")
        self.setGeometry(100, 100, 400, 300)

        # Create layout
        layout = QVBoxLayout()

        # Shutter mode buttons
        shutter_layout = QHBoxLayout()
        self.mode_buttons = []
        layout.addWidget(QLabel("Camera Shutter Mode"))
        for i, mode in enumerate(["Full-mannul", "Timing", "Temperature Difference", "Full-automatic"]):
            button = QPushButton(mode)
            button.clicked.connect(lambda _, m=i: self.set_shutter_mode(m))
            shutter_layout.addWidget(button)
            self.mode_buttons.append(button)
        layout.addLayout(shutter_layout)

        # Brightness slider
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(50)
        self.brightness_slider.valueChanged.connect(self.set_brightness)
        layout.addWidget(QLabel("Brightness"))
        layout.addWidget(self.brightness_slider)

        # Contrast slider
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(0, 100)
        self.contrast_slider.setValue(50)
        self.contrast_slider.valueChanged.connect(self.set_contrast)
        layout.addWidget(QLabel("Contrast"))
        layout.addWidget(self.contrast_slider)

        # Query button
        query_button = QPushButton("Query")
        query_button.clicked.connect(self.query_settings)
        layout.addWidget(query_button)

        # Save settings button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(save_current_settings)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def set_shutter_mode(self, mode):
        set_shutter_mode(mode)
        QMessageBox.information(self, "Info", f"Shutter mode set to {self.mode_buttons[mode].text()}")

    def set_brightness(self):
        brightness = self.brightness_slider.value()
        set_brightness(brightness)

    def set_contrast(self):
        contrast = self.contrast_slider.value()
        set_contrast(contrast)

    def query_settings(self):
        mode = get_shutter_mode()
        brightness = get_brightness()
        contrast = get_contrast()

        mode_text = ["Full-mannul", "Timing", "Temperature Difference", "Full-automatic"]
        QMessageBox.information(self, "Current Settings",
                                f"Shutter Mode: {mode_text[mode]}\n"
                                f"Brightness: {brightness}\n"
                                f"Contrast: {contrast}")

    def closeEvent(self, event):
        close_connection()

def close_connection():
    if ser.is_open:
        ser.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraControlApp()
    window.show()
    sys.exit(app.exec())
