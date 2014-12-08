import socket
import threading
import json
import time
import random
from p2pbazaar import trackerPort

class Tracker:
    def __init__(self, debug=False, inTrackerPort = trackerPort):
        self.debug = debug
        self.trackerPort = inTrackerPort
        self.listenThread = ListenThread(thisTracker = self, port = self.trackerPort)
        self.activeNodeDict = {}
        self.listenReadyEvent = threading.Event()
        self.shutdownFlag = False
        self.nodeReplyEvent = threading.Event()
        self.lastNodeReply = None
        self.dataLock = threading.RLock()
        self.searchRequestsSentList = []
        self.searchRequestsReceivedDict = {}
    
    def startup(self):
        self.listenThread.start()
        return self.listenThread.readyEvent.wait(10)
    
    def disconnectNode(self, otherID):
        targetNodeThread = self.activeNodeDict[otherID]
        msg = self._makeDC()
        targetNodeThread.send(msg)
        targetNodeThread.shutdownFlag = True
        
    def handleReceivedNode(self, inPacketData, connectThread):
        data = json.loads(inPacketData)
        if "type" in data:
            if data["type"] == "thisisme":
                self._handleTIM(inData = data, connectThread = connectThread)
                return True
            elif data["type"] == "ping":
                self._handlePing(connectThread = connectThread)
                return True
            elif data["type"] == "nodereq":
                self._handleNodeReq(data, connectThread)
                return True
            elif data["type"] == "error":
                self._handleError(inData = data, connectThread = connectThread)
                return True
            elif data["type"] == "dc":
                self._handleDC(connectThread = connectThread)
                return True
        return False
        
    
    def shutdown(self):
        self.shutdownFlag = True
        self.dataLock.acquire()
        for thread in self.activeNodeDict.values():
            thread.shutdownFlag = True
        self.dataLock.release()
        self.listenThread.shutdownFlag = True
        if self.debug:
            print "Tracker shutdown."
        
    def _makePing(self):
        returnMsg = json.dumps({"type":"ping"})
        return returnMsg
        
    def _makeDC(self):
        returnMsg = json.dumps({"type":"dc"})
        return returnMsg
        
    def _makeNodeReply(self, id):
        self.dataLock.acquire()
        port = self.activeNodeDict[id].nodePort
        self.dataLock.release()
        returnMsg = json.dumps({"type":"nodereply", "id":id, "port":port})
        return returnMsg
        
    def _makeError(self, errorCode, readableMsg = None):
        msgDict = {"type":"error", "code":errorCode}
        if readableMsg != None:
            msgDict["info"] = readableMsg
        returnMsg = json.dumps(msgDict)
        return returnMsg
        
    def _makeTIY(self, id):
        returnMsg = json.dumps({"type":"thisisyou", "id":id})
        return returnMsg
        
    
    def _handleTIM(self, inData, connectThread):
        if "id" and "port" in inData:
            newID = inData["id"]
            port = inData["port"]
            if newID == -1:
                self.dataLock.acquire()
                while newID == -1 or newID in self.activeNodeDict:
                    newID = random.randint(0, 1000000)
                self.dataLock.release()
            connectThread.dataLock.acquire()
            connectThread.nodePort = port
            if connectThread.nodeID != newID:
                self.dataLock.acquire()
                if connectThread.nodeID in self.activeNodeDict:
                    del self.activeNodeDict[connectThread.nodeID]
                self.activeNodeDict[newID] = connectThread
                self.dataLock.release()
                connectThread.nodeID = newID
                if not connectThread.connectedEvent.isSet():
                    connectThread.connectedEvent.set()
                connectThread.expectingPing = False
                connectThread.dataLock.release()
                msg = self._makeTIY(newID)
                connectThread.send(msg)
                return True
            connectThread.dataLock.release()
        return False
        
    def _handlePing(self, connectThread):
        if not connectThread.expectingPing:
            msg = self._makePing()
            connectThread.send(msg)
            return True
        else:
            connectThread.expectingPing = False
            return False
            
    def _handleError(self, inData, connectThread):
        if "code" in inData:
            errorCode = inData["code"]
            if errorCode == "notiy":
                id = connectThread.nodeID
                self.dataLock.acquire()
                while id == -1 or id in self.activeNodeDict:
                    id = random.randint(0, 1000000)
                self.dataLock.release()
                msg = self._makeTIY(id)
                connectThread.send(msg)
                return ("notiy", None)
            return ("Unrecognized message", None)
        return ("Bad message", None)
            
    def _handleDC(self, connectThread):
        connectThread.shutdownFlag = True
        
    def _handleSearch(self, inData):
        if "id" in inData and "returnPath" in inData:
            self.passOnSearchRequest(inData)
            return True
        return False
        
    def _handleNodeReq(self, data, connectThread):
        if "id" in data:
            id = data["id"]
            self.dataLock.acquire()
            if id not in self.activeNodeDict:
                self.dataLock.release()
                return False
            else:
                self.dataLock.release()
                msg = self._makeNodeReply(id)
                connectThread.send(msg)
                return True
        elif "idList" in data:
            idList = data["idList"]
            self.dataLock.acquire()
            if set(idList) == set(self.activeNodeDict.keys()):
                self.dataLock.release()
                msg = self._makeError("gotnothing", "You're already connected to every node I've got!")
                connectThread.send(msg)
                return False
            else:
                id = -1
                while id == -1 or id in idList:
                    id = random.choice(self.activeNodeDict.keys())
                self.dataLock.release()
                msg = self._makeNodeReply(id)
                connectThread.send(msg)
                return True
        return False
    
    def _handleNodeReply(self, inData):
        if ("id" in inData 
            and "port" in inData
            and self.trackerThread.expectingNodeReply):
            self.connectNode(otherID = inData["id"], otherNodePort = inData["port"])
            self.nodeReplyEvent.set()
            self.trackerThread.expectingNodeReply = False
            return True
        return False
        
        
class ListenThread(threading.Thread):
    def __init__(self, thisTracker, port):
        threading.Thread.__init__(self, target=self.mainLoop)
        self.listenPort = port
        self.thisTracker = thisTracker
        self.shutdownFlag = False
        self.readyEvent = threading.Event()
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket.bind(('localhost', port))
        #self.listenSocket.settimeout(5)
        self.listenSocket.listen(50)
        self.thisTracker.listenSocket = self.listenSocket
        
    def mainLoop(self):
        self.readyEvent.set()
        while not self.shutdownFlag:
            try:
                newNodeSock, newSockAddr = self.listenSocket.accept()
            except socket.timeout:
                continue
            else:
                newNodeThread = NodeConnectionThread(thisTracker = self.thisTracker, nodeSocket = newNodeSock)
                newNodeThread.start()
    
class NodeConnectionThread(threading.Thread):
    def __init__(self, thisTracker, nodeSocket, otherID = -1, originHere = False):
        threading.Thread.__init__(self, target=self.receiveLoop)
        self.debug = thisTracker.debug
        self.thisTracker = thisTracker
        self.nodeSocket = nodeSocket
        self.nodePort = 0
        self.nodeID = otherID
        self.connectedEvent = NodeConnectionEvent()
        self.dcFlag = False
        #self.nodeSocket.settimeout(5)
        self.sendLock = threading.RLock()
        self.dataLock = threading.Lock()
        self.shutdownFlag = False
        self.expectingPing = False
        awaitTIMThread = threading.Thread(target=self.awaitTIM)
        awaitTIMThread.start()
        
    def receiveLoop(self):
        while not self.shutdownFlag and not self.dcFlag:
            #self.sendLock.acquire()
            try:
                dataSize = self.nodeSocket.recv(5)
                if dataSize != "":
                    recvData = self.nodeSocket.recv(int(dataSize))
            except socket.timeout:
                #self.sendLock.release()
                if self.expectingPing:
                    self.dcFlag = True
                else:
                    msg = self.thisTracker._makePing()
                    self.send(msg)
                    self.expectingPing = True
                continue
            except socket.error as e:
                self.dcFlag = True
                #self.sendLock.release()
                if self.debug:
                    print e
                continue
            else:
                #self.sendLock.release()
                if self.debug:
                    print "Tracker received message {0} from node {1}.".format(recvData, self.nodeID)
                if dataSize != "" and recvData != "":
                    self.thisTracker.handleReceivedNode(inPacketData = recvData, connectThread = self)
                    self.expectingPing = False
                else:
                    self.dcFlag = True
        self.thisTracker.dataLock.acquire()
        if self.nodeID in self.thisTracker.activeNodeDict:
            del self.thisTracker.activeNodeDict[self.nodeID]
        self.thisTracker.dataLock.release()
        try:
            self.nodeSocket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            if self.debug:
                print e
        self.nodeSocket.close()
        return
        
    def send(self, packetData):
        self.sendLock.acquire()
        messageLength = str(len(packetData)).rjust(5)
        try:
            self.nodeSocket.send(messageLength)
            self.nodeSocket.send(packetData)
            if self.debug:
                print "Tracker sent message {0} to node {1}.".format(packetData, self.nodeID)
        except socket.error:
            self.dcFlag = True
            if self.debug:
                print e
        finally:
            self.sendLock.release()
        
    def awaitTIM(self):
        if not self.connectedEvent.wait(3):
            msg = self.thisTracker._makeError(errorCode = "notim")
            self.send(msg)
        if not self.connectedEvent.wait(3):
            msg = self.thisTracker._makeError(errorCode = "notim")
            self.send(msg)
        if not self.connectedEvent.wait(4):
            self.dcFlag = True
        

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
            
        
            