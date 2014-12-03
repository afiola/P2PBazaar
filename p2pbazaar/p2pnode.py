import socket
import threading
import json
import time
from p2pbazaar import trackerPort

class P2PNode:
    def __init__(self, inTrackerPort = trackerPort):
        self.idNum = -1
        self.trackerThread = TrackerConnectionThread(port = inTrackerPort)
        self.listenThread = ListenThread()
        self.connectedNodeDict = {}
        self.listenReadyEvent = threading.Event()
        self.shutdownFlag = False
        self.nodeReplyEvent = threading.Event()
        self.lastNodeReply = None
        self.dataLock = threading.Lock()
        self.searchRequestsSentList = []
        self.searchRequestsReceivedDict = {}
    
    def startup(self):
        self.listenThread.start()
        return self.listenThread.readyEvent.wait(10)
    
    
    def trackerConnect(self):
        self.trackerThread.start()
        return self.trackerThread.connectEvent.wait(10)
        
    def requestOtherNode(self):
        msg = self._makeNodeReq()
        self.trackerThread.send(msg)
        self.trackerThread.expectingNodeReply = True
        return True
        
    def connectNode(self, otherID, otherNodePort):
        newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        newSocket.connect(('localhost', otherNodePort))
        newSockThread = NodeConnectionThread(thisNode = self, nodeSocket = newSocket, otherID = otherID, originHere = True)
        newSockThread.start()
        return newSockThread.connectEvent.wait(10)
    
    def disconnectNode(self, otherID):
        targetNodeThread = self.connectedNodeDict[otherID]
        msg = self._makeDC()
        targetNodeThread.send(msg)
        
    def handleReceivedTracker(self, inPacketData):
        data = json.loads(inPacketData)
        if "type" in data:
            if data["type"] == "thisisyou":
                self._handleTIY(inData = data, connectThread = self.trackerThread)
                return True
            elif data["type"] == "ping":
                self._handlePing(connectThread = self.trackerThread)
                return True
            elif data["type"] == "error":
                self._handleError(inData = data, connectThread = self.trackerThread)
                return True
            elif data["type"] == "dc":
                self._handleDC(connectThread = self.trackerThread)
                return True
            elif data["type"] == "nodereply":
                self._handleNodeReply(inData = data)
                return True
        return False
        
    def handleReceivedNode(self, inPacketData, connectThread):
        data = json.loads(inPacketData)
        if "type" in data:
            if data["type"] == "thisisme":
                self._handleTIM(inData = data, connectThread = connectThread)
                return True
            elif data["type"] == "ping":
                self._handlePing(connectThread = connectThread)
                return True
            elif data["type"] == "error":
                self._handleError(inData = data, connectThread = connectThread)
                return True
            elif data["type"] == "dc":
                self._handleDC(connectThread = connectThread)
                return True
            elif data["type"] == "search":
                self._handleSearch(inData = data)
                return True
        return False
        
    def passOnSearchRequest(self, searchRequest):
        searchID = searchRequest["id"]
        pathNodeIDs = searchRequest["returnPath"]
        msg = self._makeSearchReq(searchRequest)
        sentIDs = []
        self.dataLock.acquire()
        if searchID not in self.searchRequestsReceivedDict:
            self.searchRequestsReceivedDict[searchID] = []
        for id in pathNodeIDs:
            if id not in self.searchRequestsReceivedDict[searchID]:
                self.searchRequestsReceivedDict[searchID].append(id)
        if searchID not in self.searchRequestsSentList:
            for nodeID in self.connectedNodeDict.keys():
                if nodeID not in self.searchRequestsReceivedDict[searchID]:
                    self.connectedNodeDict[nodeID].send(msg)
                    sentIDs.append(nodeID)
        self.searchRequestsSentList.append(searchID)
        self.dataLock.release()
        return sentIDs
        
    
    def shutdown(self):
        self.shutdownFlag = True
                
    def _makeTIM(self):
        returnMsg = json.dumps({"type":"thisisme", "port":self.listenSocket.getsockname()[1], "id":self.idNum})
        return returnMsg
        
    def _makePing(self):
        returnMsg = json.dumps({"type":"ping"})
        return returnMsg
        
    def _makeSearchReq(self, searchRequest):
        searchRequest["returnPath"].append(self.idNum)
        returnMsg = json.dumps(searchRequest)
        return returnMsg
        
    def _makeDC(self):
        returnMsg = json.dumps({"type":"dc"})
        return returnMsg
        
    def _makeNodeReq(self):
        nodeIDList = [self.idNum]
        self.dataLock.acquire()
        for id in self.connectedNodeDict.keys():
            nodeIDList.append(id)
        self.dataLock.release()
        returnMsg = json.dumps({"type":"nodereq", "idList":nodeIDList})
        return returnMsg
        
    def _makeError(self, errorCode, readableMsg = None):
        msgDict = {"type":"error", "code":errorCode}
        if readableMsg != None:
            msgDict["info"] = readableMsg
        returnMsg = json.dumps(msgDict)
        return returnMsg
        
    def _handleTIM(self, inData, connectThread):
        if "id" in inData:
            newID = inData["id"]
            connectionThread.dataLock.acquire()
            if connectionThread.nodeID != newID:
                self.dataLock.acquire()
                if connectionThread.nodeID in self.connectedNodeDict:
                    del self.connectedNodeDict[connectionThread.nodeID]
                self.connectedNodeDict[newID] = connectionThread
                self.dataLock.release()
                connectionThread.nodeID = newID
                if not connectionThread.connectedEvent.isSet():
                    connectionThread.connectedEvent.set()
                connectionThread.expectingPing = False
                connectionThread.dataLock.release()
                return True
            connectionThread.dataLock.release()
        return False
        
    def _handleTIY(self, inData, connectThread):
        if "id" in inData and connectThread is self.trackerThread:
            newID = inData["id"]
            if newID > 0:
                self.idNum = newID
                connectThread.connectEvent.set()
                return True
        return False
        
    def _handlePing(self, connectThread):
        if not connectionThread.expectingPing:
            msg = self._makePing()
            connectionThread.send(msg)
            return True
        else:
            connectionThread.expectingPing = False
            return False
            
    def _handleError(self, inData, connectThread):
        if "code" in inData:
            errorCode = data["code"]
            if errorCode == "notim":
                msg = self._makeTIM()
                connectionThread.send(msg)
                return ("notim", None)
            return ("Unrecognized message", None)
        return ("Bad message", None)
            
    def _handleDC(self, connectThread):
        connectionThread.shutdownFlag = True
        
    def _handleSearch(self, inData):
        if "id" in inData and "returnPath" in inData:
            self.passOnSearchRequest(inData)
            return True
        return False
        
    def _handleNodeReply(self, inData):
        if ("id" in inData 
            and "port" in inData
            and self.trackerThread.expectingNodeReply):
            self.connectNode(otherID = inData["id"], otherPort = inData["port"])
            self.trackerThread.expectingNodeReply = False
            return True
        return False
        
        
class ListenThread(threading.Thread):
    def __init__(self, listenSocket, thisNode):
        threading.Thread.__init__(self, target=self.mainLoop)
        self.thisNode = thisNode
        self.shutdownFlag = False
        self.readyEvent = threading.Event()
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket.bind(('localhost', 0))
        self.listenSocket.settimeout(5)
        self.listenSocket.listen(5)
        
    def mainLoop(self):
        self.readyEvent.set()
        while not self.shutdownFlag:
            try:
                newNodeSock, newSockAddr = self.listenSocket.accept()
            except socket.timeout:
                continue
            else:
                newNodeThread = NodeConnectionThread(thisNode = self.thisNode, nodeSocket = newNodeSock)
                newNodeThread.start()
    
class NodeConnectionThread(threading.Thread):
    def __init__(self, thisNode, nodeSocket, otherID = -1, originHere = False):
        threading.Thread.__init__(self, target=self.receiveLoop)
        self.thisNode = thisNode
        self.nodeSocket = nodeSocket
        self.nodePort = nodeSocket.getsockname()[1]
        self.nodeID = otherID
        self.connectedEvent = NodeConnectionEvent()
        self.dcFlag = False
        self.nodeSocket.settimeout(5)
        self.sendLock = threading.Lock()
        self.dataLock = threading.Lock()
        self.expectingPing = False
        if originHere:
            msg = self.thisNode._makeTIM()
            self.send(msg)
            self.connectedEvent.set()
            self.thisNode.connectedNodeDict[otherID] = self
        else:
            awaitTIMThread = threading.Thread(target=self.awaitTIM)
            awaitTIMThread.start()
        
    def receiveLoop(self):
        while not self.shutdownFlag and not self.dcFlag:
            try:
                recvData = nodeSocket.recv(4096)
            except socket.timeout:
                continue
            else:
                sentPing = False
                if recvData != "":
                    self.thisNode.handleReceivedNode(inPacketData = recvData, connectThread = self)
                else:
                    self.dcFlag = True
        self.thisNode.dataLock.acquire()
        del self.thisNode.connectedNodeDict[self.nodeID]
        self.thisNode.dataLock.release()
        self.nodeSocket.shutdown(socket.SHUT_RDWR)
        self.nodeSocket.close()
        return
        
    def send(self, packetData):
        self.sendLock.acquire()
        self.nodeSocket.send(packetData)
        self.sendLock.release()
        
    def awaitTIM(self):
        if not self.connectedEvent.wait(3):
            msg = self.thisNode._makeError(code = "notim")
            self.send(msg)
        if not self.connectedEvent.wait(3):
            msg = self.thisNode._makeError(code = "notim")
            self.send(msg)
        if not self.connectedEvent.wait(4):
            self.dcFlag = True
        
class TrackerConnectionThread(threading.Thread):
    def __init__(self, thisNode, trackerPort):
        threading.Thread.__init__(self, target=self.trackerLoop)
        self.thisNode = thisNode
        self.trackerPort = trackerPort
        self.trackerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connectEvent = threading.Event()
        self.shutdownFlag = False
        self.expectingNodeReply = False
        self.sendLock = threading.Lock()
        
        self.trackerSocket.settimeout(5)
        self.trackerSocket.connect(('localhost', self.trackerPort))
        msg = self._makeTIM()
        self.trackerSocket.send(msg)
        awaitTIYThread = threading.Thread(target=self.awaitTIY)
        awaitTIYThread.start()
        
    def trackerLoop(self):
        dcFlag = False
        while not self.shutdownFlag and not dcFlag:
            try:
                response = self.trackerSocket.recv(4096)
            except socket.timeout:
                pass
            else:
                if response != "":
                    nextMsg, responseData = self.handleReceivedTracker(inPacketData = response)
                else:
                    dcFlag = True
        self.trackerSocket.shutdown(socket.SHUT_RDWR)
        self.trackerSocket.close()
        
    def send(self, packetData):
        self.sendLock.acquire()
        self.trackerSocket.send(packetData)
        self.sendLock.release()
        
    def awaitTIY(self):
        while not self.connectEvent.isSet():
            if not self.connectEvent.wait(3):
                msg = self.thisNode._makeError(code = "notim")
                self.send(msg)
        

class NodeConnectionEvent():
    def __init__(self):
        self._event = threading.Event()
        
    def isSet(self):
        return self._event.isSet()
    
    def set(self):
        return self._event.set()
    
    def clear(self):
        return self._event.clear()
        
    def wait(self, timeout = None):
        if timeout <= 0 or timeout == None:
            return self._event.wait()
        else:
            return self._event.wait(timeout)
            
        
            