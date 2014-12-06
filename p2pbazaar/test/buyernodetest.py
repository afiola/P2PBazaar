import socket
import threading
import unittest
import json
from p2pbazaar.buyernode import BuyerNode
from p2pbazaar.test import mocks
from p2pbazaar import trackerPort


class BuyerNodeTest(unittest.TestCase):
    def setUp(self):
        self.testNode = BuyerNode()
        
    def tearDown(self):
        self.testNode.shutdown()
        
class SearchItemTestCase(BuyerNodeTest):
    def runTest(self):
        mockThreadList = []
        for n in range(3):
            mockThreadList.append(mocks.MockThread())
            mockThreadList[n].nodeID = n+2001
            self.testNode.connectedNodeDict[n+2001] = mockThreadList[n]
        self.assertEquals(self.testNode.searchItem("socks"),[2001,2002,2003])    
                
        self.testNode.searchItem("socks")
        
        data = [json.loads(thread.sentMsg) for thread in mockThreadList]
        
        expectedDict = {"type":"search", "returnPath":[self.testNode.idNum], "item":"socks"}
        
        for item in data:
            self.assertIn("type", item)
            self.assertEquals(item["type"], expectedDict["type"])
            self.assertIn("returnPath", item)
            self.assertEquals(item["returnPath"], expectedDict["returnPath"])
            self.assertIn("item", item)
            self.assertEquals(item["item"], expectedDict["item"])
            self.assertIn("id", item)
        
        
class BuyItemTestCase(BuyerNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
        
        self.testNode.connectedNodeDict[mockThread.nodeID] = mockThread
        
        self.testNode.buyItem(sellerID = mockThread.nodeID, targetItem = "socks")
        
        recvData = json.loads(mockThread.sentMsg)
        
        self.assertIn("type", recvData)
        self.assertEquals(recvData["type"], "buy")
        self.assertIn("item", recvData)
        self.assertEquals(recvData["item"], "socks")
        self.assertIn("id", recvData)
        
        '''buyID = recvData["id"]
        
        message = json.dumps({"type":"buyOK", "item":"socks", "id":buyID})
        mockNode1.send(message)
        self.testNode.handleReceivedNode(inPacketData = testSock1.recv(4096))
        self.assertTrue(self.testNode.buyCompleteEvent.wait(5))
        self.assertIn("socks", self.testNode.shoppingBag)'''
    
class HandleReceivedNodeTestCase(BuyerNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
        
        
        #Test BuyOK
        msg = json.dumps({"type":"buyOK"})
        self.assertTrue(self.testNode.handleReceivedNode(msg, mockThread))
        
        #Test SearchReply
        msg = json.dumps({"type":"reply"})
        self.assertTrue(self.testNode.handleReceivedNode(msg, mockThread))
        
        #Test ping (make sure inherited is working)
        msg = json.dumps({"type":"ping"})
        self.assertTrue(self.testNode.handleReceivedNode(msg, mockThread))
        
        #Test unrecognized message
        msg = json.dumps({"type":"lolwat"})
        self.assertFalse(self.testNode.handleReceivedNode(msg, mockThred))
        
        
        return
if __name__ == "__main__":
    unittest.main()
        
        
        