import socket
import threading
import json
import time
from p2pbazaar import trackerPort

EVT_BAD_MSG = "Missing or unrecognized message type"
EVT_NODE_CONNECT = "Node {0} has successfully connected!"
EVT_NODE_IDUPDATE = "Node {0} ID updated to {1}."
EVT_NODE_NOUPDATE = "Node {0} already known!"
EVT_MSG_NOID = "Missing ID number in {0} message from {1}."
EVT_NOT_TRACKER = "Received a {0} message from a source other than the tracker."
EVT_PING_RESPONDED = "Got a ping from {0} and sent one back."
EVT_PING_GOTREPLY = "{0} responded to ping."
EVT_TRACKER_CONNECT = "Successfully connected to tracker."
EVT_NOTIM_REPLY = "Got a NOTIM from {0} and resent"

class P2PNode:
    def __init__(self, debug=0, inTrackerPort = trackerPort):
        self.debug = debug
        self.idNum = -1
        self.trackerThread = TrackerConnectionThread(thisNode = self, trackerPort = inTrackerPort)
        self.listenThread = ListenThread(thisNode = self)
        self.connectedNodeDict = {}
        self.listenReadyEvent = threading.Event()
        self.shutdownFlag = False
        self.nodeReplyEvent = NodeReplyEvent()
        self.lastNodeReply = None
        self.dataLock = threading.RLock()
        self.searchRequestsSentList = []
        self.searchRequestsReceivedDict = {}
        self.allThreadsList = []
    
    def startup(self):
        self.listenThread.start()
        return self.listenThread.readyEvent.wait(5)
    
    
    def trackerConnect(self):
        self.trackerThread.start()
        return self.trackerThread.connectEvent.wait(5)
        
    def requestOtherNode(self):
        msg = self._makeNodeReq()
        self.trackerThread.send(msg)
        self.nodeReplyEvent.clear()
        self.trackerThread.expectingNodeReply = True
        return self.nodeReplyEvent.wait(5)
        
    def connectNode(self, otherID, otherNodePort):
        newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        newSocket.connect(('localhost', otherNodePort))
        newSockThread = NodeConnectionThread(thisNode = self, nodeSocket = newSocket, otherID = otherID, originHere = True)
        newSockThread.start()
        return newSockThread.connectedEvent.wait(10)
    
    def disconnectNode(self, otherID):
        targetNodeThread = self.connectedNodeDict[otherID]
        msg = self._makeDC()
        targetNodeThread.send(msg)
        targetNodeThread.shutdownFlag = True
        
    def handleReceivedTracker(self, inPacketData, event):
        data = json.loads(inPacketData)
        if "type" in data:
            if data["type"] == "thisisyou":
                self._handleTIY(inData = data, connectThread = self.trackerThread, event = event)
            elif data["type"] == "ping":
                self._handlePing(connectThread = self.trackerThread, event = event)
            elif data["type"] == "error":
                self._handleError(inData = data, connectThread = self.trackerThread, event = event)
            elif data["type"] == "dc":
                self._handleDC(connectThread = self.trackerThread, event = event)
            elif data["type"] == "nodereply":
                self._handleNodeReply(inData = data, event = event)
            return event.wait(5)
        event.set(success = False, message = EVT_BAD_MSG)
        return False
    
    def handleReceivedNode(self, inPacketData, connectThread, event):
        data = json.loads(inPacketData)
        if "type" in data:
            if data["type"] == "thisisme":
                self._handleTIM(inData = data, connectThread = connectThread, event = event)
            elif data["type"] == "ping":
                self._handlePing(connectThread = connectThread, event = event)
            elif data["type"] == "error":
                self._handleError(inData = data, connectThread = connectThread, event = event)
            elif data["type"] == "dc":
                self._handleDC(connectThread = connectThread, event = event)
            elif data["type"] == "search":
                self._handleSearch(inData = data, event = event)
            return event.wait(5)
        event.set(success = False, message = EVT_BAD_MSG)
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
        self.dataLock.acquire()
        for thread in self.connectedNodeDict.values():
            thread.shutdownFlag = True
        self.dataLock.release()
        self.trackerThread.shutdownFlag = True
        self.listenThread.shutdownFlag = True
        if self.debug:
            print "Node {0} shutdown.".format(self.idNum)
                
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
        
    def _handleTIM(self, inData, connectThread, event):
        if "id" in inData:
            newID = inData["id"]
            connectThread.dataLock.acquire()
            oldID = connectThread.nodeID
            if oldID != newID:
                self.dataLock.acquire()
                if oldID in self.connectedNodeDict:
                    del self.connectedNodeDict[oldID]
                self.connectedNodeDict[newID] = connectThread
                self.dataLock.release()
                connectThread.nodeID = newID
                if not connectThread.connectedEvent.isSet():
                    connectThread.connectedEvent.set()
                    event.set(success = True, message = EVT_NODE_CONNECT.format(newID))
                else:
                    event.set(success = True, message = EVT_NODE_IDUPDATE.format(oldID, newID))
                connectThread.expectingPing = False
                connectThread.dataLock.release()
                return True
            event.set(success = False, message = EVT_NODE_NOUPDATE.format(newID))
            connectThread.dataLock.release()
        event.set(success = False, message = EVT_MSG_NOID.format("ThisIsMe", "Node {0}".format(connectThread.nodeID)))
        return False
        
    def _handleTIY(self, inData, connectThread, event):
        if connectThread is self.trackerThread:
            if "id" in inData 
                newID = inData["id"]
                if newID > 0:
                    self.idNum = newID
                    connectThread.connectEvent.set()
                    event.set(success = True, message = EVT_TRACKER_CONNECT)
                    return True
            event.set(success = False, message = EVT_MSG_NOID.format("ThisIsYou", "tracker"))
        event.set(success = False, message = EVT_NOT_TRACKER.format("ThisIsYou"))
        return False
        
    def _handlePing(self, connectThread, event):
        if not connectThread.expectingPing:
            msg = self._makePing()
            connectThread.send(msg)
            event.set(success = True, message = EVT_PING_RESPONDED.format(connectThread.nodeID))
            return True
        else:
            connectThread.expectingPing = False
            event.set(success = True, message = EVT_PING_GOTREPLY.format(connectThread.nodeID))
            return False
            
    def _handleError(self, inData, connectThread, event):
        if "code" in inData:
            errorCode = inData["code"]
            if errorCode == "notim":
                msg = self._makeTIM()
                connectThread.send(msg)
                event.set(success = True, message = 
                return ("notim", None)
            return ("Unrecognized message", None)
        return ("Bad message", None)
            
    def _handleDC(self, connectThread):
        connectThread.shutdownFlag = True
        
    def _handleSearch(self, inData):
        if "id" in inData and "returnPath" in inData:
            self.passOnSearchRequest(inData)
            return True
        return False
        
    def _handleNodeReply(self, inData):
        if ("id" in inData 
            and "port" in inData
            and self.trackerThread.expectingNodeReply):
            self.connectNode(otherID = inData["id"], otherNodePort = inData["port"])
            self.nodeReplyEvent.set(True)
            self.trackerThread.expectingNodeReply = False
            return True
        return False
        
        
class ListenThread(threading.Thread):
    def __init__(self, thisNode):
        threading.Thread.__init__(self, target=self.mainLoop)
        self.thisNode = thisNode
        self.shutdownFlag = False
        self.readyEvent = threading.Event()
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket.bind(('localhost', 0))
        self.listenSocket.settimeout(10)
        self.listenSocket.listen(5)
        self.thisNode.listenSocket = self.listenSocket
        
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
        self.debug = thisNode.debug
        self.thisNode = thisNode
        self.nodeSocket = nodeSocket
        self.nodePort = nodeSocket.getsockname()[1]
        self.nodeID = otherID
        self.connectedEvent = NodeConnectionEvent()
        self.dcFlag = False
        self.nodeSocket.settimeout(10)
        self.sendLock = threading.RLock()
        self.dataLock = threading.RLock()
        self.shutdownFlag = False
        self.expectingPing = False
        if originHere:
            msg = self.thisNode._makeTIM()
            self.send(msg)
            self.thisNode.dataLock.acquire()
            self.thisNode.connectedNodeDict[otherID] = self
            self.thisNode.dataLock.release()
            self.connectedEvent.set()
        else:
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
                if not self.shutdownFlag and not self.dcFlag:
                    if self.expectingPing:
                        self.dcFlag = True
                    else:
                        msg = self.thisNode._makePing()
                        self.send(msg)
                        self.expectingPing = True
                continue
            except socket.error as e:
                self.dcFlag = True
                if self.debug:
                    print e
                continue
            else:
                if dataSize != "" and recvData != "":
                    if self.debug:
                        print "Node {0} received message {1} from node {2}.".format(self.thisNode.idNum, recvData, self.nodeID)
                    event = MessageHandledEvent()
                    self.thisNode.handleReceivedNode(inPacketData = recvData, connectThread = self, event = event)
                    self.expectingPing = False
                    if self.debug and not event.isSet():
                        print "Error: Message not handled."
                else:
                    self.dcFlag = True
            finally:
                #self.sendLock.release()
                pass
        self.thisNode.dataLock.acquire()
        if self.nodeID in self.thisNode.connectedNodeDict:
            del self.thisNode.connectedNodeDict[self.nodeID]
        self.thisNode.dataLock.release()
        try:
            self.nodeSocket.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            if self.debug:
                print e.reason
        self.nodeSocket.close()
        return
        
    def send(self, packetData):
        messageLength = str(len(packetData)).rjust(5)
        try:
            self.sendLock.acquire()
            self.nodeSocket.send(messageLength)
            self.nodeSocket.send(packetData)
            if self.debug:
                print "Node {0} sent message {1} to node {2}.".format(self.thisNode.idNum, packetData, self.nodeID)
        except socket.error as e:
            self.dcFlag = True
            if self.debug:
                print e
        finally:
            self.sendLock.release()
        
    def awaitTIM(self):
        if not self.connectedEvent.wait(3):
            msg = self.thisNode._makeError(errorCode = "notim")
            self.send(msg)
        if not self.connectedEvent.wait(3):
            msg = self.thisNode._makeError(errorCode = "notim")
            self.send(msg)
        if not self.connectedEvent.wait(4):
            self.dcFlag = True
        
class TrackerConnectionThread(threading.Thread):
    def __init__(self, thisNode, trackerPort):
        threading.Thread.__init__(self, target=self.trackerLoop)
        self.debug = thisNode.debug
        self.thisNode = thisNode
        self.trackerPort = trackerPort
        self.trackerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.trackerSocket.settimeout(10)
        self.connectEvent = threading.Event()
        self.shutdownFlag = False
        self.expectingNodeReply = False
        self.expectingPing = False
        self.sendLock = threading.RLock()
        self.nodeID = "tracker"
        
        
    def trackerLoop(self):
        self.trackerSocket.connect(('localhost', self.trackerPort))
        msg = self.thisNode._makeTIM()
        self.send(msg)
        awaitTIYThread = threading.Thread(target=self.awaitTIY)
        awaitTIYThread.start()
        dcFlag = False
        while not self.shutdownFlag and not dcFlag:
            #self.sendLock.acquire()
            try:
                dataSize = self.trackerSocket.recv(5)
                if dataSize != "":
                    response = self.trackerSocket.recv(int(dataSize))
            except socket.timeout:
                if not self.shutdownFlag and not self.dcFlag:
                    if self.expectingPing:
                        self.shutdownFlag = True
                        self.thisNode.shutdown()
                    else:
                        self.expectingPing = True
                        msg = self.thisNode._makePing()
                        self.send(msg)
            except socket.error as e:
                self.dcFlag = True
                if self.debug:
                    print e
            else:
                if self.debug:
                    print "Node {0} received message {1} from tracker.".format(self.thisNode.idNum, response)
                if dataSize != "" and response != "":
                    event = MessageHandledEvent()
                    self.thisNode.handleReceivedTracker(inPacketData = response)
                    self.expectingPing = False
                    if self.debug and not event.isSet():
                        print "Error: Message not handled."
                else:
                    dcFlag = True
            #self.sendLock.release()
        self.trackerSocket.shutdown(socket.SHUT_RDWR)
        self.trackerSocket.close()
        
    def send(self, packetData):
        self.sendLock.acquire()
        messageLength = str(len(packetData)).rjust(5)
        try:
            self.trackerSocket.send(messageLength)
            self.trackerSocket.send(packetData)
            if self.debug and "ping" not in packetData:
                print "Node {0} sent message {1} to tracker.".format(self.thisNode.idNum, packetData)
        except socket.error as e:
            self.dcFlag = True
            if self.debug:
                print e
        self.sendLock.release()
        
        
    def awaitTIY(self):
        while not self.connectEvent.wait(3) and not self.shutdownFlag:
            msg = self.thisNode._makeError(errorCode = "notiy")
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
        return self._event.wait()
            
class NodeReplyEvent():
    def __init__(self):
        self._event = threading.Event()
        self._success = False
    def isSet(self):
        return self._event.isSet()
    
    def set(self, success):
        self._success = success
        return self._event.set()
    
    def clear(self):
        return self._event.clear()
        
    def wait(self, timeout = None):
        if self._event.wait():
            return self._success
            
class MessageHandledEvent():
    def __init__(self):
        self._condition = threading.Event()
        self.message = None
        self.success = False
        
    def isSet(self):
        return self._event.isSet()
    
    def set(self, success = True, message = None):
        self.success = success
        self.message = message
        return self._event.set()
    
    def clear(self):
        return self._event.clear()
        
    def wait(self, timeout = None):
        return self._event.wait()