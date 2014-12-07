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
        self.buyCompleteEvents = []
        self.searchReplyEvent = SearchReplyEvent()
        self.shoppingList = []
        for arg in args:
            self.shoppingList.append(str(arg))
        self.shoppingBag = []
        self.pendingBuyDict = {}
        self.activeSearchDict = {}
        random.seed()
        self.buyReadyThread = threading.Thread(target=self._buyReadyLoop)
        
    def startup(self):
        P2PNode.startup(self)
        self.buyReadyThread.start()
        
    def searchItem(self, targetItem):
        searchID = random.randint(1, 1000000)
        msg = self._makeSearch(item = targetItem, searchID = searchID)
        newSearchThread = AwaitSearchReplyThread(thisNode = self, item = targetItem, searchID = searchID)
        self.dataLock.acquire()
        self.buyCompleteEvents.append(BuyCompleteEvent(targetItem))
        self.activeSearchDict[searchID] = newSearchThread
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
        for thread in self.activeSearchDict.values():
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
            buyEventResult = self.buyReady.wait(1)
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
                print "Bought a {0}!".format(boughtItem)
                for event in self.buyCompleteEvents:
                    if event.item == boughtItem:
                        event.set(True)
                        break
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
                and item not in self.shoppingBag
                and item not in self.pendingBuyDict.values()
                and searchID in self.activeSearchDict):
                del self.activeSearchDict[searchID]
                self.dataLock.release()
                self.buyReady.set(item, connectThread.nodeID)
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
                        for event in self.buyCompleteEvents:
                            if event.item == thread.item:
                                event.set(False)
                        print "Couldn't find {0}. :(".format(thread.item)
                        thread.stopFlag = True
                        del self.activeSearchDict[id]
                        stoppedThreadIDs.append(id)
                        
                self.dataLock.release()
                return ("gotnothing", stoppedThreadIDs)
            else:
                return P2PNode._handleError(inData, connectThread)
        else:
            return ("Bad message", None)
            
    def goShopping(self):
        self.startup()
        self.trackerConnect()
        for item in self.shoppingList:
            self.searchItem(item)
        for thread in self.activeSearchDict.values():
            thread.join()
        for event in self.buyCompleteEvents:
            event.wait()
        print "Shopping results:"
        print "Bought: ",
        for item in self.shoppingBag:
            print item,
        if len(self.shoppingBag) < len(self.shoppingList)
        print "\nCouldn't find any: ",
        for item in self.shoppingList:
            if item not in self.shoppingBag:
            print item,
        print "\n"
        
        
        
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
            
class BuyCompleteEvent():
    def __init__(self, item):
        self._event = threading.Event()
        self.item = item
        self.success = None
    def isSet(self):
        return self._event.isSet()
    
    def set(self, success):
        self.success = success
        return self._event.set()
    
    def clear(self):
        self.success = None
        return self._event.clear()
        
    def wait(self, timeout):
        if self._event.wait(timeout):
            return (self.item, self.success)
        else:
            return None
        
        
class SearchReplyEvent():
    def __init__(self):
        self._event = threading.Event()
        self._queue = collections.deque()
        self._lock = threading.Lock()
        
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
            
    def waitFor(self, id, timeout=None):
        startTime = time.time()
        while (not timeout) or (startTime - time.time() < timeout):
            if self._queue and self._queue[0] == id and self._event.wait(timeout):
                retVal = self._queue.popleft()
                return retVal
            time.sleep(0.5)
        return None
        
class AwaitSearchReplyThread(threading.Thread):
    def __init__(self, thisNode, item, searchID, timeout=10):
        threading.Thread.__init__(self, target=self.waitLoop)
        self.thisNode = thisNode
        self.item = item
        self.searchID = searchID
        self.hasFailed = False
        self.stopFlag = False
        self.timeout = timeout
        
    def waitLoop(self):
        startTime = time.time()
        replyEvent = self.thisNode.searchReplyEvent
        while not self.stopFlag:
            timeLeft = self.timeout - (time.time()-startTime)
            replyID = replyEvent.waitFor(self.searchID, timeLeft)
            if replyID == None:
                self.hasFailed = True
                self.thisNode.requestOtherNode()
            else:
                self.stopFlag = True
        return 
        
                
                
                    
            
            