import socket
import threading
import unittest
import json
import time
from p2pbazaar.sellernode import SellerNode
from p2pbazaar.test import mocks
from p2pbazaar import trackerPort


class SellerNodeTest(unittest.TestCase):
    def setUp(self):
        self.testNode = SellerNode()
        
    def tearDown(self):
        self.testNode.shutdown()
        
class HandleReceivedNodeTestCase(SellerNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
        self.testNode.connectedNodeDict[mockThread.nodeID] = mockThread
        
        #Test Buy request
        msg = json.dumps({"type":"buy"})
        self.assertTrue(self.testNode.handleReceivedNode(msg, mockThread))
        
        #Test search
        msg = json.dumps({"type":"search"})
        self.assertTrue(self.testNode.handleReceivedNode(msg, mockThread))
        
        #Test ping (make sure inherited is working)
        msg = json.dumps({"type":"ping"})
        self.assertTrue(self.testNode.handleReceivedNode(msg, mockThread))
        
        #Test unrecognized message
        msg = json.dumps({"type":"lolwat"})
        self.assertFalse(self.testNode.handleReceivedNode(msg, mockThread))
        
        
class ReplyTest(SellerNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
       
        self.testNode.connectedNodeDict[mockThread.nodeID] = mockThread
        
        self.assertTrue(self.testNode.reply(mockThread.nodeID, 1))
        time.sleep(2)
        expectedDict = {"type":"reply", "searchID":1}
        self.assertEquals(json.loads(mockThread.sendMsg), expectedDict)
        
        
if __name__ == "__main__":
    unittest.main()