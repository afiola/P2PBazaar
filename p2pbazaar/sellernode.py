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
            
        self.buyRequestsReceived = []
        
    def startup(self):
        P2PNode.startup(self)
        
    def shutdown(self):
        P2PNode.shutdown(self)
        
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
        pass
        
    def _handleBuyRequest(self, data, connectThread):
        pass
        
    def _handleSearch(self, data):
        pass
        
    