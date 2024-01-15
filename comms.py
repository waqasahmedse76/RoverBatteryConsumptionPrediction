"""
Manages communication with Rover
Connection must be started from ui through a <listening> thread
SYST-395
"""

import socket, time, pathlib, threading


_ADDR = '192.168.4.1', 10000
CWD = pathlib.Path(__file__).resolve().parent
LOGS = CWD / 'logs'


class RoverComm:
    def __init__(self, syst_addr=(), log=False):
        self.address = syst_addr if syst_addr else _ADDR
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.commands = {'fwd': 'Move forward', 'rev': 'Move back', 'halt': 'Stop',
                         'left': 'Turn left', 'right': 'Turn right',
                         'gripup': 'Grip up', 'gripdown': 'Grip down'}
        self.data = {'time': [], 'accel': [], 'current': [], 'voltage': [], 'gyro': [], 'mag': [], 'range': []}
        self.listeners = []
        self.logging = log
        self.logfiles = []
        if log:
            for key in self.data:
                if key != 'time':
                    file = LOGS / f"{key}_log: {time.ctime()}"
                    file.write_text(f'time,{key}\n')
                    self.logfiles.append(file)
        self.listening = threading.Thread(target=self.listen, daemon=True)
        self.listening.start()

    def register_listener(self, *listener):
        self.listeners.extend(listener)

    def transmit(self, cmd):
        if cmd in self.commands.keys():
            try:
                self.sock.sendto(bytes(f"{cmd}", 'utf-8'), self.address)
            except Exception as e:
                return f"Error transmitting command: {cmd}\nDetails:\n{e}"
            else:
                return f""

    def broadcast(self):
        for listener in self.listeners:
            listener.update(self.data)

    def log(self):
        for file in self.logfiles:
            if key := [file.name.startswith(k) for k in self.data]:
                file.write_text(f"{self.data[time][-1]},")
                file.write_text(f"{self.data[key[0]][-1]}\n")

    def listen(self):
        s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # s1.connect(('10.0.0.0', 0))
        s1.connect(_ADDR)
        addr = s1.getsockname()[0]

        self.sock.bind((addr, 10000))
        while 1:
            d, _ = self.sock.recvfrom(255)  # wait for UDP packet
            d = d.decode('utf-8')  # convert to string
            e = d.split(',')  # split values
            self.data['time'].append(time.strftime("%H %M %S"))
            self.data['range'].append(e[0])  # set label with new ultrasonic range value
            self.data['mag'].append(e[1])  # compass
            self.data['voltage'].append(e[2])
            self.data['current'].append(e[3])
            self.data['accel'].append([e[4], e[5], e[6]])
            self.data['gyro'].append([e[7], e[8], e[9]])
            self.broadcast()
            if self.logging:
                self.log()
            # print(self.data)
            time.sleep(1)


if __name__ == '__main__':
    a = RoverComm()
    a.listen()
