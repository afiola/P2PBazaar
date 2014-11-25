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
        self.nodeReplyEvent = threading.Event()
        self.lastNodeReply = None
        self.trackerConnected = False
        self.trackerLock = threading.Lock()
    
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
        
    def requestOtherNode(self, inTrackerSocket = None):
        trackerSocket = None
        data = None
        if inTrackerSocket == None:
            trackerSocket = self.trackerSocket
        else:
            trackerSocket = inTrackerSocket
        msg = json.dumps({"type":"nodereq"})
        if self.trackerConnected:
            self.trackerLock.acquire()
        trackerSocket.send(msg)
        if self.trackerConnected:
            self.trackerLock.release()
            if not self.nodeReplyEvent.wait(5):
                return None
            else:
                data = self.lastNodeReply
                self.nodeReplyEvent.unset()
        else:
            data = json.loads(trackerSocket.recv(4096))
        if data["type"] == "nodereply" and "id" in data and "port" in data:
            return (data["id"], data["port"])
        else:
            return None
        
        
    def connectNode(self, otherID, otherNodePort):
        newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        newSocket.connect(('localhost', otherNodePort))
        doneEvent = threading.Event()
        newSockThread = threading.Thread(target = self._nodeConnectionLoop, kwargs = {"socket":newSocket, "addr":newSocket.getsockname(), "originHere":True, "event":doneEvent, "otherID":otherID})
        newSockThread.start()
        if doneEvent.wait(5):
            return True
        else:
            return False
        
    
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
        elif inExpectingPing:
            if data["type"] == "ping":
                retData = True
        else:
            if data["type"] == "ping":
                retMsg = self._makePing()
            elif data["type"] == "error":
                if data["code"] == "notim":
                    retMsg = self._makeTIM()
            elif data["type"] == "nodereply":
                retData = {"id":data["id"], "port":data["port"]}
                self.lastNodeReply = retData
                self.nodeReplyEvent.set()
        return (retMsg, retData)
        
    def handleReceivedNode(self, inPacketData, inExpectingPing = False, inExpectingTIM = False):
        data = json.loads(inPacketData)
        retMsg = None
        retData = None
        if inExpectingTIM and "type" in data and data["type"] == "thisisme":
            retData = {"nodeID":data["id"]}
        return (retMsg, retData)
            
        
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
        dcFlag = False
        inDoneEvent.set()
        while not self.shutdownFlag and not dcFlag:
            self.trackerLock.acquire()
            try:
                response = self.trackerSocket.recv(4096)
            except socket.timeout:
                pass
            else:
                if response != "":
                    nextMsg, responseData = self.handleReceivedTracker(inPacketData = response)
                else:
                    dcFlag = True
            self.trackerLock.release()
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
        doneEvent = None
        if "event" in kwargs:
            doneEvent = kwargs["event"]
        dcFlag = False
        nodeSocket.settimeout(5)
        if kwargs["originHere"]:
            msg = self._makeTIM()
            nodeSocket.send(msg)
        else:
            while otherID == -1:
                try:
                    recvData = nodeSocket.recv(4096)
                except socket.timeout:
                    continue
                else:
                    responseMSG, data = self.handleReceivedNode(inPacketData = recvData, inExpectingTIM = True)
                    if "nodeID" in data:
                        otherID = data["nodeID"]
        self.connectedNodeDict[otherID] = nodeSocket
        if doneEvent != None:
            doneEvent.set()
        sentPing = False
        while not self.shutdownFlag and not dcFlag:
            try:
                recvData = nodeSocket.recv(4096)
            except socket.timeout:
                continue
            else:
                sentPing = False
                if recvData != "":
                    responseMSG, data = self.handleReceivedNode(inPacketData = recvData, inExpectingPing = sentPing)
                    if responseMSG:
                        nodeSocket.send(responseMSG)
                    if data:
                        if "dcFlag" in data and data["dcFlag"]:
                            dcFlag = True
                        elif "isSearchRequest" in data and data["isSearchRequest"]:
                            passOnSearchRequest(data["origSearchReq"])
                else:
                    dcFlag = True
        nodeSocket.shutdown(socket.SHUT_RDWR)
        nodeSocket.close()
        return
                
    def _makeTIM(self):
        returnMsg = json.dumps({"type":"thisisme", "port":self.listenSocket.getsockname()[1], "id":self.idNum})
        return returnMsg
        
    def _makePing(self):
        returnMsg = json.dumps({"type":"ping"})
        return returnMsg
        