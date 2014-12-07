import json
import threading
import socket
import random
import time
from sys import argv
from socket import timeout
from p2pbazaar import trackerPort
from p2pbazaar.exceptions import *

class Tracker():
    #Initialize tracker. Does *not* actually start tracking.
    #inPort: Port the tracker will use to accept incoming connections.
    #inDebug: Chooses whether to output status messages.
    def __init__(self,  inPort=trackerPort, 
                        inDebug=False, 
                        inTestMode=False, 
                        inHostName='localhost'):
        random.seed()
        self.debug = inDebug
        self.testMode = inTestMode
        self.hostName = inHostName
        self.connectLock = threading.RLock()
        self.connectLock.acquire()
        self.quitFlag = False
        self.listenPort = inPort
        self.activeNodeDict = {}
        self.connThreadList = []
        self.lastConnTime = time.time()
        self.connectLock.release()
    
    #Actually starts tracking on the designated port.
    def startup(self):
        self.listenThread = threading.Thread(target = self._listenLoop, name = "ListenThread")
        self.listenThread.start()
    
    #Loop that listens for and accepts incoming connections. Will disconnect if
    #a connected node does not send a properly formatted ThisIsMe message.
    #If there are no active connections for 30 seconds, shuts down the tracker
    #and prompts the user to restart or quit.
    def _listenLoop(self):
        #Restart-or-quit loop:
        while not self.quitFlag:
            with self.connectLock:
                try:
                    #Initialize and bind listen socket.
                    self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    #In order to prevent program from hanging indefinitely,
                    #listen socket silently times out and restarts every 0.5 seconds.
                    self.listenSocket.settimeout(0.5)            
                    self.listenSocket.bind((self.hostName, self.listenPort))
                except socket.error:
                    #self.connectLock.release()
                    continue
                self.listenSocket.listen(5)
            #Listen for and establish new connections.
            pauseListenFlag = False
            while not pauseListenFlag and not self.quitFlag:
                try:
                    newConn, newConnAddr = self.listenSocket.accept()
                    '''If a new connection is detected, awaits a ThisIsMe
                    message containing the new node's listen port.
                    If none is received after 5 seconds, or if it gets a non-ThisIsMe
                    message, tracker will send back a NoTIM error message up to 5 times
                    before giving up and closing the connection.'''
                    newConnPort = -1
                    newConn.settimeout(5.0)
                    failCount = 0
                    while newConnPort == -1 and failCount <= 5:
                        try:
                            recvData = json.loads(newConn.recv(4096).decode('utf-8'))
                            newConnPort = self._handleFirstTIM(recvData)
                        except timeout:
                            pass #Silent timeout
                        if newConnPort == -1:
                            self._sendError(inSocket=newConn, inCode="notim")
                            failCount += 1
                            if failCount >= 5:
                                raise BadConnectionException(badConnSocket = newConn, msg="Too many bad ThisIsMe messages!")
                    '''If the new node *does* send a proper ThisIsMe, tracker assigns it
                    an ID number and adds the node to its various lists and dicts. It also
                    resets the time since last connection.'''
                    newID=random.randint(0, 100000)
                    self.connectLock.acquire()
                    while newID in self.activeNodeDict:
                        newID = random.randint(0, 100000)
                    newConnDict = {"socket":newConn, "port":newConnPort}
                    self.activeNodeDict[newID] = newConnDict
                    newConnThread = threading.Thread(target = self._activeConnLoop, kwargs = {"id":newID, "connDict":newConnDict}, name = "ConnThread{0}".format(newID))
                    self.connThreadList.append(newConnThread)
                    self.lastConnTime = time.time()
                    self.connectLock.release()
                    newConnThread.start()
                #Handle a normal timeout. Triggers shutdown ("pause") if no active
                #connections for 30 seconds.
                except timeout:
                    '''if (not self.activeNodeDict) and ((time.time() - self.lastConnTime) > 30 or (self.testMode and time.time() - self.lastConnTime > 5)):
                        pauseListenFlag = True'''
                    pass
                #If a node can't seem to get its ThisIsMe right, shut down the connection.
                except BadConnectionException as e:
                    self._closeSocket(inSocket = e.badSocket, inID = e.badID, inReceivedDC = False)
            #This chunk only runs once there have been no active connections
            #for 30 seconds, and asks the user to restart or quit.
            '''if not self.testMode:
                print "No active connections. Tracker has shut down."
                shouldQuitInput = ""
                while shouldQuitInput != 'r' and shouldQuitInput != 'q':
                    shouldQuitInput = raw_input("Enter 'r' to restart or 'q' to quit: ")[0].lower()
                    if shouldQuitInput == 'q':
                        self.quitFlag = True
                        print "Goodbye!"
                    elif shouldQuitInput == 'r':
                        print "Restarting..."
            else:
                self.quitFlag = True'''
        
    #Handles the ThisIsMe message sent by a node connecting to the tracker
    #for the first time. Needs only to grab a valid listen port.
    #inData: Dictionary containing the message information.
    #Returns the port number in the TIM message, otherwise -1 to indicate an error.
    def _handleFirstTIM(self, inData):
        try:
            #Checks that the message is actually a ThisIsMe.
            if ("type" not in inData) or (inData["type"] != "thisisme"):
                return -1
            #Checks that the message contains a valid port number.
            elif ("port" not in inData) or (inData["port"] <= 0 or inData["port"] >= 65536):
                return -1
            else:
                return inData["port"]
        #If the port number isn't actually a number, returns an error.
        except TypeError:
            return -1
    
    #Sends a ThisIsYou message to a node, containing the node's assigned
    #ID number.
    #socket: Valid, open socket to send the message to.
    #ID: Node's newly assigned ID number.
    def _sendTIY(self, inSocket, inID):
        message = json.dumps({"type":"thisisyou", "id":inID})
        inSocket.send(message)
    
    #Sends an error message to a node, containing an error
    #code and an optional human-readable message.
    #socket: Valid, open socket to send the message to.
    #code: Short, parseable error code. May check against a list of valid codes.
    #readableMsg: Optional human-readable message explaining the error.
    def _sendError(self, inSocket, inCode, inReadableMsg=None):
        message = None
        if inReadableMsg != None:
            message = json.dumps({"type":"error", "code":inCode, "info":inReadableMsg})
        else:
            message = json.dumps({"type":"error", "code":inCode})
        inSocket.send(message)
    
    #Sends a ping to a node.
    def _sendPing(self, inSocket):
        message = json.dumps({"type":"ping"})
        inSocket.send(message)
        
    def _sendNodeReply(self, inSocket, inID, inPort):
        message = json.dumps({"type":"nodereply", "id":inID, "port":inPort})
        inSocket.send(message)
        
    def _closeSocket(self, inSocket, inID):
        inSocket.shutdown(socket.SHUT_RDWR)
        inSocket.close()
        #print "Socket ID {0} closed".format(inID)
        self.connectLock.acquire()
        #print "Socket ID {0} close method has lock".format(inID)
        if inID in self.activeNodeDict:
            self.activeNodeDict[inID].clear()
            del self.activeNodeDict[inID]
        del inSocket
        self.connectLock.release()
        #print "Socket ID {0} close method released lock".format(inID)
        
    
    #Loop that pmanages a connection to a single node.
    #kwargs: Dictionary containing:
    #   "id": Unique ID number assigned to the node.
    #   "connDict": Dictionary with socket and listen port for the node.
    def _activeConnLoop(self, **kwargs):
        connID = kwargs["id"]
        connDict = kwargs["connDict"]
        connSocket = connDict["socket"]
        connPort = connDict["port"]
        dcFlag = False
        connSocket.settimeout(0.5)
        lastConnTime = time.time()
        receivedDC = False
        #Send a ThisIsYou message to the node with its ID number
        self._sendTIY(inSocket = connSocket, inID = connID)
        
        #Now that connection is properly established, await incoming messages.
        #(Like always, times out silently to avoid hanging.)
        isExpectingPing = False
        sentPing15 = False
        sentPing30 = False
        sentPing45 = False
        while not self.quitFlag and not dcFlag:
            try:
                received = connSocket.recv(4096).decode('utf-8')
                if received == "":
                    dcFlag = True
                    if self.debug:
                        #print "Tracker received empty string"
                        pass
                else:
                    recvData = json.loads(received)
                    if self.debug:
                        #print "Tracker received data from {0}: {1}".format(connID, recvData)
                        pass
                    lastConnTime = time.time()
                    self.handleReceived(inSocket = connSocket, inID = connID, inData = recvData, expectingPing = isExpectingPing)
                    isExpectingPing = False
                    sentPing15 = False
                    sentPing30 = False
                    sentPing45 = False
            except timeout:
                pass
            except ValueError:
                if self.debug:
                    #print "Sending error message to {0}".format(connID)
                    pass
                self._sendError(inSocket = connSocket, inCode = "wtf")
            except socket.error as e:
                if self.debug:
                    #print "Connection {0} terminated unexpectedly".format(connID)
                    #print e
                    pass
                dcFlag = True
            deltaTime = time.time() - lastConnTime
            #if self.debug:
                #print "Current deltaTime for connection {0}: {1}".format(connID, deltaTime)
            if deltaTime >= 60 and not dcFlag:
                dcFlag = True
                #print "Set DCFlag for ID {0}.".format(connID)
            elif deltaTime >= 45 and not dcFlag and not self.testMode and not sentPing45:
                self._sendPing(inSocket = connSocket)
                isExpectingPing = True
                sentPing45 = True
            elif deltaTime >= 30 and not dcFlag:
                if(self.testMode):
                    dcFlag = True
                    if self.debug:
                        pass
                        #print "Set DCFlag for ID {0}.".format(connID)
                elif not sentPing30:
                    self._sendPing(inSocket = connSocket)
                    isExpectingPing = True
                    sentPing30 = True
            elif deltaTime >= 15 and not dcFlag and not sentPing15:
                if self.debug:
                    #print "ID {0} is awfully quiet, sending ping...".format(connID)
                    pass
                self._sendPing(inSocket = connSocket)
                isExpectingPing = True
                sentPing15 = True
        #print "Closing socket ID #{0}...".format(connID)
        self._closeSocket(inSocket = connSocket, inID = connID)
        return
    
    def shutdown(self):
        self.quitFlag = True
        
        
            
    
    #Handles incoming messages when the tracker isn't expecting
    #anything specific. Returns True only if the corresponding
    #socket sent a disconnect message, False otherwise
    def handleReceived(self, inSocket, inID, inData, expectingPing = False):
        if "type" not in inData:
            if self.debug:
                #print "Sending missing type error to {0}".format(inID)
                pass
            self._sendError(inSocket = inSocket, inCode = "wtf", inReadableMsg = "Missing message type")
        elif inData["type"] == "thisisme":
            self.connectLock.acquire()
            if "port" in inData:
                try:
                    if (inData["port"] + 0) > 0:
                        self.activeNodeDict[inID] = {"socket": inSocket, "port":inData["port"]}
                    else:
                        if self.debug:
                            #print "Sending invalid port error to {0}".format(inID)
                            pass
                        self._sendError(inSocket = inSocket, inCode = "wtf", inReadableMsg = "Port must be greater than 0.")
                except TypeError:
                    if self.debug:
                        #print "Sending invalid port error to {0}".format(inID)
                        pass
                    self._sendError(inSocket = inSocket, inCode = "wtf", inReadableMsg = "Port must be a number.")
            self.connectLock.release()
        elif inData["type"] == "ping":
            if not expectingPing:
                if self.debug:
                    #print "Sending ping to {0}".format(inID)
                    pass
                self._sendPing(inSocket = inSocket)
        elif inData["type"] == "nodereq":
            if "id" not in inData or inData["id"] <= 0 or inData["id"] not in self.activeNodeDict:
                if "idList" not in inData or set(inData["idList"]) != set(self.activeNodeDict.keys()):
                    targetID = -1
                    self.connectLock.acquire()
                    while ( targetID not in self.activeNodeDict 
                            or ("idList" in inData and targetID in inData["idList"])
                            or targetID == inID):
                        targetID = random.choice(self.activeNodeDict.keys())
                    if self.debug:
                        #print "Sending NodeReply to {0}".format(inID)
                        pass
                    self._sendNodeReply(inSocket = inSocket, inID = targetID, inPort = self.activeNodeDict[targetID]['port'])
                    self.connectLock.release()
                else:
                    self._sendError(inSocket = inSocket, inCode = "gotnothing", 
                                    inReadableMsg = "You're already connected to every node I've got!")
            else:
                targetID = inData["id"]
                self._sendNodeReply(inSocket = inSocket, inID = targetID, inPort = self.activeNodeDict[targetID]['port'])
        else: 
            if self.debug:
                #print "Sending unrecognized message type error to {0}".format(inID)
                pass
            self._sendError(inSocket = inSocket, inCode = "wtf", inReadableMsg = "Unrecognized message type.")
            
            
        
    
#End of Tracker class.

if __name__ == "__main__":
    listenPort = trackerPort
    if "-p" in argv:
        pIndex = argv.index("-p")
        if argv[pIndex+1].isdigit() and int(argv[pIndex+1]) > 0 and int(argv[pIndex+1] <= 65535):
            listenPort = int(argv[pIndex+1])
    if "-v" in argv:
        debug = True
    else:
        debug = False
    tracker = Tracker(inPort = listenPort, inDebug = debug)