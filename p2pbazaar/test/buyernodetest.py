import socket
import threading
import unittest
import json
from p2pbazaar.buyernode import BuyerNode
from p2pbazaar import trackerPort

class BuyerNodeTest(unittest.TestCase):
    def setUp(self):
        self.testNode = BuyerNode()
        self.mockNode1Listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mockNode2Listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mockNode3Listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mockNode1Listen.bind(('localhost',0))
        self.mockNode2Listen.bind(('localhost',0))
        self.mockNode3Listen.bind(('localhost',0))
        self.mockNode1Listen.listen(5)
        self.mockNode2Listen.listen(5)
        self.mockNode3Listen.listen(5)
        
        
    def tearDown(self):
        self.testNode.shutdown()
        del self.testNode
        
class SearchItemTestCase(BuyerNodeTest):
    def runTest(self):
        testSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testSock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testSock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testSock1.connect(self.mockNode1Listen.getsockname())
        mockNode1, mockNode1Addr = self.mockNode1Listen.accept()
        testSock2.connect(self.mockNode2Listen.getsockname())
        mockNode2, mockNode2Addr = self.mockNode2Listen.accept()
        testSock3.connect(self.mockNode3Listen.getsockname())
        mockNode3, mockNode3Addr = self.mockNode3Listen.accept()
        
        self.testNode.connectedNodeDict[1] = testSock1
        self.testNode.connectedNodeDict[2] = testSock2
        self.testNode.connectedNodeDict[3] = testSock3
        
        self.testNode.searchItem("socks")
        
        data = [json.loads(mockNode1.recv(4096)), json.loads(mockNode2.recv(4096)), json.loads(mockNode3.recv(4096))]
        
        expectedDict = {"type":"search", "returnPath":[self.testNode.idNum], "item":"socks", "id":1}
        
        for item in data:
            assertIn("type", item)
            assertEquals(item["type"], expectedDict["type"])
            assertIn("returnPath", item)
            assertEquals(item["returnPath"], expectedDict["returnPath"])
            assertIn("item", item)
            assertEquals(item["item"], expectedDict["item"])
            assertIn("id", item)
            
        
        
class BuyItemTestCase(BuyerNodeTest):
    def runTest(self):
        pass
    
class HandleReceivedNodeTestCase(BuyerNodeTest):
    def runTest(self):
        pass
        
class HandleSearchReplyTestCase(BuyerNodeTest):
    def runTest(self):
        pass