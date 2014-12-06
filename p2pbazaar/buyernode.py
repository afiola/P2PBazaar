from p2pbazaar.p2pnode import P2PNode
import threading
import json
import random
import time
import collections
from p2pbazaar import trackerPort

class BuyerNode(P2PNode):
    def __init__(self, *args):
        P2PNode.__init__(self)
        self.buyReady = BuyReadyEvent()
        self.buyCompleteEvent = threading.Event()
        self.searchReplyEvent = SearchReplyEvent()
        self.shoppingList = []
        for arg in args:
            self.shoppingList.append(str(arg))
        self.shoppingBag = []
        self.buyTargetDict = {}
        self.pendingBuyDict = {}
        self.activeSearchDict = {}
        self.searchReplyThreadList=[]
        random.seed()
        self.buyReadyThread = threading.Thread(target=self._buyReadyLoop)
        
    def startup(self):
        P2PNode.startup(self)
        self.buyReadyThread.start()
        
    def searchItem(self, targetItem):
        searchID = random.randint(1, 1000000)
        msg = self._makeSearch(item = targetItem, searchID = searchID)
        newSearchThread = AwaitSearchReplyThread(thisNode = self, searchID = searchID)
        self.dataLock.acquire()
        self.searchReplyThreadList.append(newSearchThread)
        self.searchRequestsSentList.append(searchID)
        self.searchRequestsReceivedDict[searchID] = []
        sentNodes = []
        for node in self.connectedNodeDict.values():
            node.send(msg)
            sentNodes.append(node.nodeID)
        self.dataLock.release()
        newSearchThread.start()
        return sentNodes
        
    def shutdown(self):
        P2PNode.shutdown(self)
        for thread in self.searchReplyThreadList:
            thread.stopFlag = True
        
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
            return True
        return False
        
    def handleReceivedNode(self, inPacketData, connectThread):
        data = json.loads(inPacketData)
        if "type" in data:
            if data["type"] == "buyOK":
                self._handleBuyOK(data)
            elif data["type"] == "reply":
                self._handleSearchReply(data, connectThread)
            else:
                return P2PNode.handleReceivedNode(self, inPacketData, connectThread)
            return True
        return False

    def _makeBuy(self, item, buyID):
        msg = json.dumps({"type":"buy", "id":buyID, "item":item})
        return msg
        
    def _makeSearch(self, item, searchID = None):
        if not searchID:
            searchID = random.randint(1, 1000000)
        msg = json.dumps({"type":"search", "returnPath":[self.idNum], "item":item, "id":searchID})
        return msg
        
    def _buyReadyLoop(self):
        while not self.shutdownFlag:
            buyEventResult = self.buyReady.wait(5)
            if buyEventResult:
                targetItem, targetSeller = buyEventResult
                self.buyItem(targetSeller, targetItem)
                
    def _handleBuyOK(self, data):
        self.dataLock.acquire()
        id = None
        if "id" in data:
            id = data["id"]
            if id in self.pendingBuyDict:
                boughtItem = self.pendingBuyDict[id]
                self.shoppingBag.append(boughtItem)
                self.shoppingBag.remove(boughtItem)
                self.dataLock.release()
                return True
        self.dataLock.release()
        return False
        
    def _handleSearchReply(self, data, connectThread):
        if "item" in data and "searchID" in data:
            item = data["item"]
            searchID = data["searchID"]
            self.dataLock.acquire()
            if (item in self.shoppingList 
                and searchID in self.activeSearchDict):
                del self.activeSearchDict[searchID]
                self.dataLock.release()
                self.buyItem(connectThread.nodeID, item)
                return True
            self.dataLock.release()
        return False
    
    def _handleError(self, inData, connectThread):
        if "code" in inData:
            if inData["code"] == "gotnothing":
                self.dataLock.acquire()
                stoppedThreadIDs = []
                for id, thread in self.activeSearchDict.items():
                    if thread.hasFailed:
                        thread.stopFlag = True
                        del self.activeSearchDict[id]
                        stoppedThreadIDs.append(id)
                self.dataLock.release()
                return ("gotnothing", stoppedThreadIDs)
            else:
                return P2PNode._handleError(inData, connectThread)
        else:
            return ("Bad message", None)
        
        
class BuyReadyEvent():
    def __init__(self):
        self._event = threading.Event()
        self._queue = collections.deque()
        
    def isSet(self):
        return self._event.isSet()
    
    def set(self, item, sellerID):
        self._queue.append((item, sellerID))
        return self._event.set()
    
    def clear(self):
        return self._event.clear()
        
    def wait(self, timeout = None):
        if self._queue and self._event.wait(timeout):
            retVal = self._queue.popleft()
            return retVal
        else:
            return False
        
class SearchReplyEvent():
    def __init__(self):
        self._event = threading.Event()
        self._queue = collections.deque()
        
    def isSet(self):
        return (self._queue and self._event.isSet())
    
    def set(self, searchID):
        self._queue.append(searchID)
        return self._event.set()
    
    def clear(self):
        if not self._queue:
            return self._event.clear()
        
    def wait(self, timeout = None):
        if self._queue and self._event.wait(timeout):
            retVal = self._queue.popleft()
            return retVal
        else:
            return None
            
            
        
class AwaitSearchReplyThread(threading.Thread):
    def __init__(self, thisNode, searchID, timeout=10):
        threading.Thread.__init__(self, target=self.waitLoop)
        self.thisNode = thisNode
        self.searchID = searchID
        self.hasFailed = False
        self.stopFlag = False
        self.timeout = timeout
        
    def waitLoop(self):
        startTime = time.time()
        replyEvent = self.thisNode.searchReplyEvent
        while not self.stopFlag:
            timeLeft = self.timeout - (time.time()-startTime)
            replyID = replyEvent.wait(timeLeft)
            if replyID == None:
                self.hasFailed = True
                self.thisNode.requestOtherNode()
            elif replyID != self.searchID:
                replyEvent.set(replyID)
            else:
                self.stopFlag = True
        return 
        
                
                
                    
            
            