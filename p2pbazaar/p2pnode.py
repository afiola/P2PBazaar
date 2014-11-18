import socket
import threading
from p2pbazaar import trackerPort

class P2PNode:
    def __init__(self, inTrackerPort = trackerPort):
        self.idNum = -1
        self.trackerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connectedNodeDict = {}
        self.connectLock = threading.Lock()
        