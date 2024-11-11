This program is created for project semiconductor laser cooling by Yang Ding from Departement of Chemistry, University of Notre Dame. This project is created to monitor the temperature change using thermal camera.

Major Features:
* Streaming a live video from thermal imaging camera after clicking "Live" button. Three region of interest (red, green, blue) will be created during stearming.
* Capturing live video with three ROIs after clicking "Acquire" button. The corresponding mean gray intensity in the ROIs will be simutanously monitored and spectralized as function of time in program.
* Clicking "Stop" button will stop the live streaming and automatically save the video to default Windows_user_Video path if acquistion was ongoing.
* "Save" button is used to save the temperature change data.
* Controllor of thermal camera for shutter mode, brightness, and cotrast through serial communication.

Packages used:
* PyQt6
* numpy
* pandas
* matplotlib
* opencv-python
* pyserial

Python Version:3.11.9
