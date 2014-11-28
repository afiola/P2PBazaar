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
        self.mockNode1Listen.settimeout(5)
        self.mockNode2Listen.settimeout(5)
        self.mockNode3Listen.settimeout(5)
        self.mockNode1Listen.listen(5)
        self.mockNode2Listen.listen(5)
        self.mockNode3Listen.listen(5)
        
        
    def tearDown(self):
        self.testNode.shutdown()
        del self.testNode
        self.mockNode1Listen.shutdown(socket.SHUT_RDWR)
        self.mockNode1Listen.close()
        self.mockNode2Listen.shutdown(socket.SHUT_RDWR)
        self.mockNode2Listen.close()
        self.mockNode3Listen.shutdown(socket.SHUT_RDWR)
        self.mockNode3Listen.close()
        
class SearchItemTestCase(BuyerNodeTest):
    def runTest(self):
        testSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testSock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testSock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testSock1.settimeout(5)
        testSock2.settimeout(5)
        testSock3.settimeout(5)
        testSock1.connect(self.mockNode1Listen.getsockname())
        mockNode1, mockNode1Addr = self.mockNode1Listen.accept()
        mockNode1.settimeout(5)
        testSock2.connect(self.mockNode2Listen.getsockname())
        mockNode2, mockNode2Addr = self.mockNode2Listen.accept()
        mockNode2.settimeout(5)
        testSock3.connect(self.mockNode3Listen.getsockname())
        mockNode3, mockNode3Addr = self.mockNode3Listen.accept()
        mockNode3.settimeout(5)
        
        self.testNode.connectedNodeDict[1] = testSock1
        self.testNode.connectedNodeDict[2] = testSock2
        self.testNode.connectedNodeDict[3] = testSock3
        
        self.testNode.searchItem("socks")
        
        data = [json.loads(mockNode1.recv(4096)), json.loads(mockNode2.recv(4096)), json.loads(mockNode3.recv(4096))]
        
        expectedDict = {"type":"search", "returnPath":[self.testNode.idNum], "item":"socks", "id":1}
        
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
        testSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testSock1.settimeout(5)
        testSock1.connect(self.mockNode1Listen.getsockname())
        mockNode1, mockNode1Addr = self.mockNode1Listen.accept()
        mockNode1.settimeout(5)
        
        self.testNode.connectedNodeDict[1] = testSock1
        
        self.testNode.buyItem(sellerID = 1, targetItem = "socks")
        
        recvData = json.loads(mockNode1.recv(4096))
        
        self.assertIn("type", recvData)
        self.assertEquals(recvData["type"], "buy")
        self.assertIn("item", recvData)
        self.assertEquals(recvData["item"], "socks")
        self.assertIn("id", recvData)
        
        buyID = recvData["id"]
        
        message = json.dumps({"type":"buyOK", "item":"socks", "id":buyID})
        mockNode1.send(message)
        self.assertTrue(self.testNode.buyCompleteEvent(5))
        self.assertIn("socks", testNode.shoppingBag)
    
class HandleReceivedNodeTestCase(BuyerNodeTest):
    def runTest(self):
        
        #Test expected ping
        msg = json.dumps({"type":"ping"})
        self.assertEquals(self.testNode.handleReceivedNode(inPacketData = msg, inExpectingPing = True), (None, True))
        
        #Test unexpected ping
        msg = json.dumps({"type":"ping"})
        self.assertEquals(self.testNode.handleReceivedNode(inPacketData = msg, inExpectingPing = False), (msg, None))
        
        #Test expected ThisIsMe
        msg = json.dumps({"type":"thisisme", "id":50})
        self.assertEquals(self.testNode.handleReceivedNode(inPacketData = msg, inExpectingTIM = True), (None, {"nodeID":50}))
        
        #Test NOTIM error
        msg = json.dumps({"type":"error", "code":"notim"})
        expectedmsg = json.dumps({"type":"thisisme", "port":self.testNode1.listenPort, "id":self.testNode1.idNum})
        self.assertEquals(self.testNode.handleReceivedNode(inPacketData = msg), (expectedmsg, None))
        
        #Test disconnect
        msg = json.dumps({"type":"dc"})
        self.assertEquals(self.testNode.handleReceivedNode(inPacketData = msg), (None, {"dcFlag":True}))
        
        #Test search
        expectedDict = {"type":"search","returnPath":[5, 7, 9], "item":"socks", "id":84}
        msg = json.dumps(expectedDict)
        self.assertEquals(self.testNode.handleReceivedNode(inPacketData = msg), (None, {"isSearchRequest":True, "origSearchReq":expectedDict}))
        
        #Test search reply
        msg = json.dumps({"type":"reply", "item":"socks", "id":5})
        expectedDict = {"isSearchReply":True, "item":"socks", "id":5}
        self.assertTrue(self.searchReplyEvent.wait(5))
        self.assertEquals(self.testNode.handleReceivedNode(inPacketData = msg), (None, expectedDict))
        return
        
class HandleSearchReplyTestCase(BuyerNodeTest):
    def runTest(self):
        self.testNode.trackerSocket.connect(self.mockNode1Listen.getsockname())
        mockTracker, mockTrackerAddr = self.mockNode1Listen.accept()
        mockTracker.settimeout(5)
        self.testNode.shoppingList.append("socks")
        testDict = {"isSearchReply":True, "item":"socks", "id":2}
        self.testNode.handleSearchReply(testDict)
        req = json.loads(mockTracker.recv(4096))
        
        self.assertIn("type", req)
        self.assertEquals(req["type"], "nodereq")
        self.assertIn("id", req)
        self.assertEquals(req["id"], 2)
        
        msg = json.dumps({"type":"nodereply", "id":2, "port":self.mockNode2Listen.getsockname()[1]})
        mockTracker.send(msg)
        mockNode2, mockAddr2 = self.mockNode2Listen.accept()
        mockNode2.settimeout(5)
        
        connectMSG = json.loads(mockNode2.recv(4096))
        
        self.assertIn("type", connectMSG)
        self.assertEquals(connectMSG["type"], "thisisme")
        self.assertIn("id", connectMSG)
        self.assertEquals(connectMSG["id"], self.testNode.idNum)
        
        self.assertTrue(self.testNode.buyReadyEvent.wait(5))
        
        self.assertIn("socks", self.testNode.buyTargetDict)
        self.assertIs(self.testNode.buyTargetDict["socks"], self.testNode.connectedNodeDict[2])
        return
        
if __name__ == "__main__":
    unittest.main()
        
        
        