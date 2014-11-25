import socket
import threading
import json
from p2pbazaar import trackerPort

class P2PNode:
    def __init__(self):
        self.idNum = -1
        self.trackerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connectedNodeDict = {}
        self.connectLock = threading.Lock()
        self.listenReadyEvent = threading.Event()
        self.shutdownFlag = False
    
    def startup(self):
        self.listenThread = threading.Thread(target = self._listenLoop)
        self.listenThread.start()
    
    
    def trackerConnect(self, inTrackerPort = trackerPort):
        self.trackerConnected = False
        trackerConnectDoneEvent = threading.Event()
        self.trackerThread = threading.Thread(target = self._trackerLoop, args = (inTrackerPort, trackerConnectDoneEvent))
        self.trackerThread.start()
        trackerConnectDoneEvent.wait(10)
        return self.trackerConnected
        
    def requestOtherNode(self, inTrackerSocket):
        pass
        
    def connectNode(self, otherID, otherNodePort):
        pass
    
    def disconnectNode(self, otherID):
        pass
        
    def handleReceivedTracker(self, inPacketData, inExpectingPing = False, inExpectingTIY = False):
        data = json.loads(inPacketData)
        retMsg = None
        retData = None
        if inExpectingTIY:
            if data["type"] == "thisisyou":
                retMsg = None
                newID = data["id"]
                retData = {"newID":newID}
        return (retMsg, retData)
        
    def handleReceivedNode(self, inPacketData, inExpectingPing = False, inExpectingTIM = False):
        pass
        
    def passOnSearchRequest(self, searchRequest):
        pass
    
    def shutdown(self):
        self.shutdownFlag = True
        
    def _trackerLoop(self, inTrackerPort, inDoneEvent = threading.Event()):
        self.trackerSocket.settimeout(5)
        self.trackerSocket.connect(('localhost', inTrackerPort))
        msg = self._makeTIM()
        self.trackerSocket.send(msg)
        response = self.trackerSocket.recv(4096)
        nextMsg, responseData = self.handleReceivedTracker(inPacketData = response, inExpectingTIY = True)
        if "newID" in responseData:
            self.idNum = responseData["newID"]
            self.trackerConnected = True
        else:
            self.trackerConnected = False
        inDoneEvent.set()
        while not self.shutdownFlag:
            try:
                response = self.trackerSocket.recv(4096)
            except socket.timeout:
                pass
            else:
                nextMsg, responseData = self.handleReceivedTracker(inPacketData = response)
        self.trackerSocket.shutdown(socket.SHUT_RDWR)
        self.trackerSocket.close()
        return
        
        
    def _listenLoop(self):
        self.listenSocket.bind(('localhost', 0))
        self.listenPort = self.listenSocket.getsockname()[1]
        self.listenSocket.settimeout(5)
        self.listenSocket.listen(5)
        self.listenReadyEvent.set()
        while not self.shutdownFlag:
            try:
                newSock, newSockAddr = self.listenSocket.accept()
            except socket.timeout:
                continue
            else:
                newSockThread = threading.Thread(target = self._nodeConnectionLoop, kwargs = {"socket":newSock, "addr":newSockAddr, "originHere":False, "otherID":-1})
                newSockThread.start()
        return
        
    def _nodeConnectionLoop(self, **kwargs):
        nodeSocket = kwargs["socket"]
        nodePort = kwargs["addr"][1]
        otherID = kwargs["otherID"]
        dcFlag = False
        nodeSocket.settimeout(5)
        if kwargs["originHere"]:
            msg = self._makeTIM(sendID = True, sendPort = False)
            nodeSocket.send(msg)
        else:
            while otherID == -1:
                try:
                    recvData = nodeSocket.recv(4096)
                except socket.timeout:
                    continue
                else:
                    responseMSG, data = handleReceivedNode(inPacketData = recvData, inExpectingTIM = True)
                    if "nodeID" in data:
                        otherID = data["nodeID"]
        self.connectedNodeDict[otherID] = nodeSocket
        sentPing = False
        while not self.shutdownFlag and not dcFlag:
            try:
                recvData = nodeSocket.recv(4096)
            except socket.timeout:
                continue
            else:
                sentPing = False
                responseMSG, data = handleReceivedNode(inPacketData = recvData, inExpectingPing = sentPing)
                if responseMSG:
                    nodeSocket.send(responseMSG)
                if data:
                    if "dcFlag" in data and data["dcFlag"]:
                        dcFlag = True
                    elif "isSearchRequest" in data and data["isSearchRequest"]:
                        passOnSearchRequest(data["origSearchReq"])
        nodeSocket.shutdown(socket.SHUT_RDWR)
        nodeSocket.close()
        return
                
    def _makeTIM(self):
        returnMsg = json.dumps({"type":"thisisme", "port":self.listenSocket.getsockname()[1], "id":self.idNum})
        return returnMsg
        
            
        