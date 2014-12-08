from p2pbazaar.p2pnode import P2PNode
import threading
import json
import random
import time
import collections
from p2pbazaar import trackerPort

class SellerNode(P2PNode):
    def __init__(self, debug = False, itemList=[]):
        P2PNode.__init__(self, debug)
        self.inventory = []
        if itemList:
            self.inventory.extend(itemList)
        self.shutdownEvent = threading.Event()
        self.purchaseRecord = []
        self.deferredReplies = {}
        
    def startup(self):
        P2PNode.startup(self)
        
    def shutdown(self):
        P2PNode.shutdown(self)
        self.shutdownEvent.set()
        
    def connectNode(self, otherID, otherNodePort):
        if P2PNode.connectNode(self, otherID, otherNodePort):
            if otherID in self.deferredReplies:
                self.reply(otherID, self.deferredReplies[otherID][1], self.deferredReplies[otherID][0])
                del self.deferredReplies[otherID]
            return True
        return False
        
    def handleReceivedNode(self, inPacketData, connectThread):
        data = json.loads(inPacketData)
        if "type" in data:
            if data["type"] == "buy":
                self._handleBuyRequest(data, connectThread)
                return True
            elif data["type"] == "search":
                self._handleSearch(data)
                return True
            else:
                return P2PNode.handleReceivedNode(self, inPacketData, connectThread)
        return False
                
        
    def reply(self, buyerID, item, searchID):
        msg = self._makeReply(item, searchID)
        self.dataLock.acquire()
        if buyerID in self.connectedNodeDict:
            self.connectedNodeDict[buyerID].send(msg)
            self.dataLock.release()
            return True
        self.dataLock.release()
        return False
        
    def requestSpecificNode(self, id):
        msg = self._makeSpecificNodeReq(id)
        self.trackerThread.send(msg)
        self.trackerThread.expectingNodeReply = True
        return True
        
    def _handleBuyRequest(self, data, connectThread):
        if "item" in data and "id" in data:
            item, id = data["item"], data["id"]
            self.dataLock.acquire()
            if item in self.inventory:
                msg = self._makeBuyOK(id)
                connectThread.send(msg)
                self.purchaseRecord.append((item, connectThread.nodeID))
                self.dataLock.release()
                return True
            self.dataLock.release()
        return False
        
    def _handleSearch(self, data):
        if "item" in data and "id" in data and "returnPath" in data:
            item = data["item"]
            id = data["id"]
            path = data["returnPath"]
            self.dataLock.acquire()
            if item in self.inventory:
                if path[0] not in self.connectedNodeDict:
                    self.deferredReplies[path[0]] = (id, item)
                    self.dataLock.release()
                    self.requestSpecificNode(path[0])
                else:
                    self.dataLock.release()
                    self.reply(path[0], item, id)
                return True
            else:
                P2PNode._handleSearch(self, data)
        return False
        
    def _makeReply(self, item, searchID):
        returnMsg = json.dumps({"type":"reply", "item":item, "searchID":searchID})
        return returnMsg
        
    def _makeSpecificNodeReq(self, id):
        returnMsg = json.dumps({"type":"nodereq", "id":id})
        return returnMsg
        
    def _makeBuyOK(self, id):
        returnMsg = json.dumps({"type":"buyOK", "id":id})
        return returnMsg
        
    def setUpShop(self):
        self.startup()
        trackerSuccess = self.trackerConnect()
        if self.debug:
            if trackerSuccess:
                print "Seller node {0} connected to tracker and received ID.".format(self.idNum)
            else:
                print "Seller node failed to connect to tracker."