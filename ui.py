"""
Dahboard/Frontend for Roger DT
"""

import sys, pathlib

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6 import uic
import pyqtgraph as pg
import qrc_resources
import pandas as pd
import numpy as np

from comms import RoverComm


CWD = '.'  # Assuming the script is in the same directory as icons and uifiles
ICON_DIR = 'C:\\Users\\SWA\\Downloads\\rover_2\\icons'
UI_DIR = 'C:\\Users\\SWA\\Downloads\\rover_2\\uifiles'
QDir.addSearchPath('icons', ICON_DIR)


pg.setConfigOptions(antialias=True)


class Dash(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.roger = RoverComm()
        self.connected = False
        self.init_ui()
        self.show()

    def init_ui(self):
        uic.loadUi(f"{UI_DIR}/win.ui", self)  # Adjusted path here
        self.setWindowTitle("DASH for Roger")
        self.setWindowIcon(QIcon('icons:roger.svg'))
        # self.setMinimumSize(1100, 700)

        # make buttons round
        for b in ("down_btn", "up_btn", "left_btn", "right_btn"):
            btn = getattr(self, b)
            btn.setFixedSize(60, 60)
        for b in ("connect_btn", "auto_btn", "off_btn"):
            btn = getattr(self, b)
            btn.setFixedSize(40, 40)
        self.connect_btn.setCheckable(True)

        # Create tabs
        # self.tabs.setTabShape(QTabWidget.TabShape.Triangular)
        self.p1 = TimeSeries(title="VI Profile")
        self.p2 = LiveTracker(title="2D Motion Tracking")
        self.roger.register_listener(self.p1) # add for voltage, current plots
        for i in range(self.tabs.count()):
            self.tabs.removeTab(i)
        self.tabs.addTab(self.p1, "V/I Profile")
        self.tabs.addTab(self.p2, "Motion Tracking")

        self.init_menus()
        self.connect_btns()

    def init_menus(self):
        main = QMenu()
        settings = main.addMenu("Settings")
        help = main.addMenu("Help")

        for i, m in zip(["settings.svg", "help.svg"], [settings, help]):
            m.setIcon(QIcon(f"icons:{i}"))
            m.setStatusTip(i.replace(".svg", ''))
            m.setToolTip(i.replace(".svg", ''))

        self.menu_btn.setMenu(main)
        # add actions

    def transmit(self, cmd):
        self.msg_board.setText(f"Sending Command:\n\t{cmd.upper()}".expandtabs(2))
        self.roger.transmit(cmd)

    def connect_btns(self):
        self.connect_btn.clicked.connect(self.connect)
        btns = "up_btn", "down_btn", "left_btn", "right_btn"
        cmds = "fwd", "rev", "left", "right"
        for b, c in zip(btns, cmds):
            btn = getattr(self, b)
            btn.pressed.connect(lambda cmd=c: self.transmit(cmd))
            btn.released.connect(lambda cmd="halt": self.transmit(cmd))

    def connect(self, *e):
        print('MQTT Subscribe: coming soon')
        pass   # connection now starts when RoverComm is initialized


class TimeSeries(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None, title=""):
        self.latest_volts = None
        self.latest_amps = None
        self.latest_power = None
        self.energy_consumed = 0
        self.total_energy = 70000
        super().__init__(parent, show=True, title=title)
        self.vplot = self.addPlot(title="Volts")   # default placement 0, 0
        self.iplot = self.addPlot(row=1, col=0, title="milliAmps")
        self.wplot = self.addPlot(row=2, col=0, title="Watts")
        self.vplot.showGrid(x=True, y=True)
        self.iplot.showGrid(x=True, y=True)
        self.wplot.showGrid(x=True, y=True)
        self.started = False
        self.vdata = self.idata = self.wdata = None

        self.check_batteries_replaced()

    def check_batteries_replaced(self):
        message = "Did you replace the batteries after the last cycle?"
        reply = QMessageBox.question(self, 'Batteries Replaced', message,
                                     QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # Batteries were replaced, set Energy_remaining to maximum
            self.total_energy = 70000
        else:
            # Batteries were not replaced, fetch the last value from Excel column E
            self.load_last_energy_remaining()

    def load_last_energy_remaining(self):
        excel_filename = 'C:\\Users\\SWA\\Downloads\\rover_2\\Testexcel\\data.xlsx'
        if pathlib.Path(excel_filename).exists():
            df = pd.read_excel(excel_filename)
            if not df.empty:
                # Get the last value in the 'Energy_remaining' column
                self.total_energy = df['Energy_remaining'].iloc[-1]
            else:
                self.total_energy = 70000
        else:
            self.total_energy = 70000   


    def get_series(self, data):
        volts, amps = data.get("voltage"), data.get("current")
        volts, amps = [float(i) for i in volts], [float(i) for i in amps]
        power = [v*i/1000 for v, i in zip(volts, amps)]
        return volts, amps, power

    def update(self, data):
        volts, amps, power = self.get_series(data)
        self.latest_volts = volts[-1]
        self.latest_amps = amps[-1]
        self.latest_power = power[-1]

        if self.latest_power is not None:
            energy_per_second = self.latest_power * 9  # Assuming voltage is in volts
            self.energy_consumed = energy_per_second

        if not self.started:
            self.started = True
            self.vdata = self.vplot.plot(volts, pen='b', name="Volts", )
            self.idata = self.iplot.plot(amps, pen='r', name="mAmps", )
            self.wdata = self.wplot.plot(amps, pen='g', name="Watts", )
        else:
            self.vdata.setData(volts)
            self.idata.setData(amps)
            self.wdata.setData(power)
            #print(amps[-1])
            #print(volts[-1])
            #print(power[-1])
            
    def save_latest_to_excel(self):
        excel_filename = 'C:\\Users\\SWA\\Downloads\\rover_2\\Testexcel\\data.xlsx'


        # Check if the Excel file already exists
        if pathlib.Path(excel_filename).exists():
            # Load the existing data from the Excel file
            df_existing = pd.read_excel(excel_filename)

            energy_consumed_per_second = self.energy_consumed
            # Calculate energy remaining by subtracting energy consumed per second
            self.total_energy = self.total_energy  - energy_consumed_per_second
            energy_remaining = self.total_energy


            # Create a DataFrame with the latest data
            df_new = pd.DataFrame({
                'Volts': [self.latest_volts],
                'mAmps': [self.latest_amps],
                'Power': [self.latest_power],
                'Energy_consumed_per_second': [self.energy_consumed],
                'Energy_remaining': [energy_remaining], 
            })

            # Concatenate the existing DataFrame with the new data
            df_updated = pd.concat([df_existing, df_new], ignore_index=True)

            # Save to Excel file with the updated data
            df_updated.to_excel(excel_filename, index=False)
        else:
            # Create a DataFrame with the latest data
            df = pd.DataFrame({
                 'Volts': [self.latest_volts],
                'mAmps': [self.latest_amps],
                'Power': [self.latest_power],
                'Energy_consumed_per_second': [self.energy_consumed],
                'Energy_remaining': [energy_remaining], 
            })

            # Save to Excel file
            df.to_excel(excel_filename, index=False)


class LiveTracker(pg.PlotWidget):
    def __init__(self, parent=None, title=""):
        super().__init__()
        self.setTitle(title)
        self.setBackground("#f5ecb5")

    def update(self, angle=0, pos=()):
        pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = Dash()

     # Add a QTimer to trigger the save to Excel every second
    timer = QTimer()
    timer.timeout.connect(win.p1.save_latest_to_excel)  # Connect to the method directly
    timer.start(1000)  # Save to Excel every 1000 milliseconds (1 second)

    sys.exit(app.exec())