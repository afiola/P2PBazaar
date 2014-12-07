from p2pbazaar.p2pnode import P2PNode
import threading
import json
import random
import time
import collections
from p2pbazaar import trackerPort

class SellerNode(P2PNode):
    def __init__(self, itemList=[], *args):
        P2PNode.__init__(self)
        
        self.inventory = []
        if itemList:
            self.inventory.extend(itemList)
        for arg in args:
            self.inventory.append(arg)
            
        self.purchaseRecord = []
        self.deferredReplies = {}
        
    def startup(self):
        P2PNode.startup(self)
        
    def shutdown(self):
        P2PNode.shutdown(self)
        
    def connectNode(self, otherID, otherNodePort):
        if P2PNode.connectNode(self, otherID, otherNodePort):
            if otherID in self.deferredReplies:
                self.reply(otherID, self.deferredReplies[otherID])
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
                
        
    def reply(self, buyerID, searchID):
        msg = self._makeReply(searchID)
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
                    self.deferredReplies[path[0]] = id
                    self.dataLock.release()
                    self.requestSpecificNode(path[0])
                else:
                    self.dataLock.release()
                    self.reply(id, path[0])
                return True
            else:
                self.passOnSearchRequest(data)
        return False
        
    def _makeReply(self, searchID):
        returnMsg = json.dumps({"type":"reply", "searchID":searchID})
        return returnMsg
        
    def _makeSpecificNodeReq(self, id):
        returnMsg = json.dumps({"type":"nodereq", "id":id})
        return returnMsg
        
    def _makeBuyOK(self, id):
        returnMsg = json.dumps({"type":"buyOK", "id":id})
        return returnMsg
        
    def setUpShop(self):
        self.startup()
        self.trackerConnect()