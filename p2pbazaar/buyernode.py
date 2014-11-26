from p2pbazaar.p2pnode import P2PNode
import threading
import json
from p2pbazaar import trackerPort

class BuyerNode(P2PNode):
    def __init__(self):
        buyCompleteEvent = threading.Event()
        pass
        
    def searchItem(self, targetItem):
        pass
        
    def buyItem(self, sellerID, targetItem):
        pass
        
    def handleReceivedNode(self, inPacketData, inExpectingPing = False, inExpectingTIM = False):
        pass
        
    def handleSearchReply(self, searchReply):
        pass