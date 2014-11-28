from p2pbazaar.p2pnode import P2PNode
import threading
import json
import random
from p2pbazaar import trackerPort

class BuyerNode(P2PNode):
    def __init__(self, *args):
        P2PNode.__init__(self)
        self.buyReadyEvent = threading.Event()
        self.buyCompleteEvent = threading.Event()
        self.searchReplyEvent = threading.Event()
        self.shoppingList = []
        for arg in args:
            self.shoppingList.append(str(arg))
        self.shoppingBag = []
        self.buyTargetDict = {}
        self.pendingBuyDict = {}
        random.seed()
        
    def searchItem(self, targetItem):
        searchID = random.randint(1, 1000000)
        msg = self._makeSearch(item = targetItem, searchID = searchID)
        self.dataLock.acquire()
        self.searchRequestsSentList.append(searchID)
        self.searchRequestsReceivedDict[searchID] = []
        for node in self.connectedNodeDict.values():
            node.send(msg)
        return
        
    def buyItem(self, sellerID, targetItem):
        if sellerID in self.connectedNodeDict:
            sellerNode = self.connectedNodeDict[sellerID]
            buyID = -1
            while buyID < 0 or buyID in self.pendingBuyDict:
                buyID = random.randint(1, 1000000)
            buyMsg = self._makeBuy(item = targetItem, buyID = buyID)
            sellerNode.send(buyMsg)
            self.dataLock.acquire()
            self.pendingBuyDict[buyID] = targetItem
            self.dataLock.release()
        return
        
    def handleReceivedNode(self, inPacketData, inExpectingPing = False, inExpectingTIM = False):
        data = json.loads(inPacketData)
        retMsg = None
        retData = None
        if "type" in data and data["type"] == "buyOK":
            boughtID = data["id"]
            self.dataLock.acquire()
            if boughtID in self.pendingBuyDict:
                boughtItem = self.pendingBuyDict[boughtID]
                self.shoppingBag.append(boughtItem)
                if boughtItem in self.shoppingList:
                    self.shoppingList.remove(boughtItem)
                self.buyCompleteEvent.set()
                retData = {"isBoughtItem":True, "id":boughtID, "item":boughtItem}
            self.dataLock.release()
            
        else:
            return P2PNode.handleReceivedNode(self, inPacketData, inExpectingPing, inExpectingTIM)
        return (retMsg, retData)
            
        
    def handleSearchReply(self, searchReply):
        if "item" in searchReply and "id" in searchReply:
            targetItem = searchReply["item"]
            targetID = searchReply["id"]
            targetNode = None
            self.dataLock.acquire()
            if targetID not in self.connectedNodeDict:
                self.dataLock.release()
                targetPort = self.requestOtherNode(inID = targetID)[1]
                self.connectNode(targetID, targetPort)
                self.dataLock.acquire()
            targetNode = self.connectedNodeDict[targetID]
            self.buyTargetDict[targetItem] = targetNode
            self.dataLock.release()
            self.buyCompleteEvent.clear()
            self.buyReadyEvent.set()
        return
            

    def _makeBuy(self, item, buyID):
        msg = json.dumps({"type":"buy", "id":buyID, "item":item})
        return msg
        
    def _makeSearch(self, item, searchID = None):
        if not searchID:
            searchID = random.randint(1, 1000000)
        msg = json.dumps({"type":"search", "returnPath":[self.idNum], "item":item, "id":searchID})
        return msg