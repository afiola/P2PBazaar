import socket
import json
import threading
from p2pbazaar import trackerPort

class MockP2PObject:
    def __init__(self, port=0):
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket.bind(('localhost', port))
        self.listenPort = self.listenSocket.getsockname()[1]
        self.listenSocket.settimeout(5)
        self.listenSocket.listen(5)
        self.nodeSocket = None
        
    def accept(self):
        self.nodeSocket = self.listenSocket.accept()[0]
        return self.nodeSocket
        
    def connect(self, port):
        self.nodeSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.nodeSocket.settimeout(5)
        self.nodeSocket.connect(('localhost',port))
        
    def sendToNode(self, msg):
        self.nodeSocket.send(msg)
        
    def receive(self):
        return self.nodeSocket.recv(4096)
        
    def receiveDict(self):
        return json.loads(self.receive())
        
    def sendPing(self):
        msg = json.dumps({"type":"ping"})
        self.sendToNode(msg)
        
    def sendError(self, code):
        msg = json.dumps({"type":"error", "code":code})
        self.sendToNode(msg)

class MockTracker(MockP2PObject):
    def __init__(self):
        MockP2PObject.__init__(self, port = trackerPort)
        
    def sendTIY(self, id):
        msg = json.dumps({"type":"thisisyou", "id":id})
        self.sendToNode(msg)

class MockNode(MockP2PObject):
    def __init__(self, id = -1, port=0):
        MockP2PObject.__init__(self, port = port)
        self.idNum = id
        
        
class MockThread:
    def __init__(self):
        self.connectEvent = threading.Event()
        self.connectedEvent = threading.Event()
        self.expectingPing = True
        self.shutdownFlag = False
        self.expectingNodeReply = False
        self.dataLock = threading.Lock()
        self.nodeID = 2001
        self.sentMsg = None
        
    def send(self, msg):
        self.sentMsg = msg
        return msg
        
    