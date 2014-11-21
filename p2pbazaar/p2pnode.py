import socket
import threading
from p2pbazaar import trackerPort

class P2PNode:
    def __init__(self):
        self.idNum = -1
        self.trackerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connectedNodeDict = {}
        self.connectLock = threading.Lock()
    
    def startup(self):
        pass
    
    
    def trackerConnect(self, inTrackerPort = trackerPort):
        pass
        
    def requestOtherNode(self, inTrackerSocket):
        pass
        
    def connectNode(self, otherID, otherNodePort):
        pass
    
    def disconnectNode(self, otherID):
        pass
        
    def handleReceivedTracker(self, inPacketData, inExpectingPing = False, inExpectingNodeRep = False):
        pass
        
    def handleReceivedNode(self, inPacketData, inExpectingPing = False, inExpectingTIM = False):
        pass
        
    def passOnSearchRequest(self, searchRequest):
        pass
    
    def shutdown(self):
        pass