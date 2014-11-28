from p2pbazaar.p2pnode import P2PNode
import threading
import json
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
        
    def searchItem(self, targetItem):
        pass
        
    def buyItem(self, sellerID, targetItem):
        pass
        
    def handleReceivedNode(self, inPacketData, inExpectingPing = False, inExpectingTIM = False):
        pass
        
    def handleSearchReply(self, searchReply):
        pass