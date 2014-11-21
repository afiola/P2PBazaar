import socket
import threading
import unittest
import json
from p2pbazaar.p2pnode import P2PNode
from p2pbazaar import trackerPort

class P2PNodeTest(unittest.TestCase):
    def setUp(self):
        self.testNode1 = P2PNode()
        self.testNode1.startup()
        self.mockTrackerListenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mockTrackerListenSocket.bind(('localhost', trackerPort))
        self.mockTrackerListenSocket.settimeout(5)
        self.mockTrackerListenSocket.listen(5)
        self.sendSocket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       
    def tearDown(self):
        self.testNode1.shutdown()
        del self.testNode1
        try:
            self.sendSocket1.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.sendSocket1.close()
        try:
            self.mockTrackerListenSocket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.mockTrackerListenSocket.close()        
        
class TrackerConnectTestCase(P2PNodeTest):
    def awaitMessageThread(self, **kwargs):
        event1 = kwargs["event1"]
        event2 = kwargs["event2"]
        id = kwargs["newID"]
        event1.set()
        testNodeTrackerSock, testNodeAddr = self.mockTrackerListenSocket.accept()
        self.recvData = json.loads(testNodeTrackerSock.recv(4096))
        event2.set()
        msg = json.dumps({"type":"thisisyou", "id":id})
        testNodeTrackerSock.send(msg)
        return
        
    
    def runTest(self):
        newID = 4000
        event1 = threading.Event()
        event2 = threading.Event()
        thread = threading.Thread(target = self.awaitMessageThread, kwargs={"event1":event1, "event2":event2, "newID":newID})
        thread.start()
        event1.wait()
        self.assertTrue(self.testNode1.trackerConnect(trackerPort))
        event2.wait()
        self.assertIn("type", self.recvData)
        self.assertEquals(self.recvData["type"], "thisisme")
        self.assertIn("port", self.recvData)
        thread.join(10)
        return
        
class RequestNodeTestCase(P2PNodeTest):
    def runTest(self):
        self.testNode1.trackerSocket.connect(('localhost', trackerPort))
        self.sendSocket1.bind(('localhost', 0))
        otherPort = self.sendSocket1.getsockname()[1]
        testNodeTrackerSock, testNodeAddr = self.mockTrackerListenSocket.accept()
        msg = json.dumps({"type":"nodereply", "id":1337, "port":otherPort})
        testNodeTrackerSock.send(msg)
        self.assertEquals(self.testNode1.requestOtherNode(self.testNode1.trackerSocket), (1337, otherPort))
        return
        
class ConnectNodeTestCase(P2PNodeTest):
    def awaitMessageThread(self, **kwargs):
        event = kwargs["event"]
        testNodeSock, testNodeAddr = self.sendSocket1.accept()
        self.recvData = json.loads(testNodeSock.recv(4096))
        return
    
    def runTest(self):
        event = threading.Event()
        self.sendSocket1.bind(('localhost', 0))
        otherID = 20
        self.sendSocket1.settimeout(5)
        self.sendSocket1.listen(5)
        thread = threading.Thread(target = self.awaitMessageThread, kwargs = {"event":event})
        thread.start()
        self.assertTrue(self.testNode1.connectNode(otherID, self.sendSocket1.getsockname()[1]))
        event.wait()
        self.assertIn("type", self.recvData)
        self.assertEquals(self.recvData["type"], "thisisme")
        self.assertIn("id", self.recvData)
        thread.join(10)
        self.assertIn(otherID, self.testNode1.connectedNodeDict)
        return

class HandleReceivedTrackerTestCase(P2PNodeTest):
    def runTest(self):
        #Test expected ping
        msg = json.dumps({"type":"ping"})
        self.assertEquals(self.testNode1.handleReceivedTracker(inPacketData = msg, inExpectingPing = True), (None, True))
        
        #Test unexpected ping
        msg = json.dumps({"type":"ping"})
        self.assertEquals(self.testNode1.handleReceivedTracker(inPacketData = msg, inExpectingPing = False), (msg, None))
        
        #Test NOTIM error
        msg = json.dumps({"type":"error", "code":"notim"})
        expectedMsg = json.dumps({"type":"thisisme", "port":self.testNode1.listenPort})
        self.assertEquals(self.testNode1.handleReceivedTracker(inPacketData = msg), (expectedMessage, None))
        
        #Test node reply
        msg = json.dumps({"type":"nodereply", "id":50, "port":1000})
        self.assertEquals(self.testNode1.handleReceivedTracker(inPacketData = msg), (None, {"id":50, "port":1000}))
        
        #Test unrecognized message
        msg = json.dumps({"type":"lolwat"})
        self.assertIsNone(self.testNode1.handleReceivedTracker(inPacketData = msg))
        
        return
        
class HandleReceivedNodeTestCase(P2PNodeTest):
    def runTest(self):
        #Test expected ping
        msg = json.dumps({"type":"ping"})
        self.assertEquals(self.testNode1.handleReceivedNode(inPacketData = msg, inExpectingPing = True), (None, True))
        
        #Test unexpected ping
        msg = json.dumps({"type":"ping"})
        self.assertEquals(self.testNode1.handleReceivedNode(inPacketData = msg, inExpectingPing = False), (msg, None))
        
        #Test expected ThisIsMe
        msg = json.dumps({"type":"thisisme", "id":50})
        self.assertEquals(self.testNode1.handleReceivedNode(inPacketData = msg, inExpectingTIM = True), (None, {"nodeID":50}))
        
        #Test NOTIM error
        msg = json.dumps({"type":"error", "code":"notim"})
        expectedmsg = json.dumps({"type":"thisisme", "id":self.testNode1.idNum})
        self.assertEquals(self.testNode1.handleReceivedNode(inPacketData = msg), (expectedmsg, None))
        
        #Test disconnect
        msg = json.dumps({"type":"dc"})
        self.assertEquals(self.testNode1.handleReceivedNode(inPacketData = msg), (None, {"dcFlag":True}))
        
        #Test search
        msg = json.dumps({"type":"search", "item":"socks", "id":84, "returnPath":[5, 7, 9]})
        expectedDict = {"returnPath":[5, 7, 9], "item":"socks", "id":84}
        self.assertEquals(self.testNode1.handleReceivedNode(inPacketData = msg), (None, {"isSearchRequest":True, "origSearchReq":expectedDict}))
        
        return
        
class PassOnSearchTestCase(P2PNodeTest):
    def runTest(self):
        self.testNode1.searchRequestSentList = [5]
        socket1 = self.sendSocket1
        socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket1.bind(('localhost', 0))
        socket2.bind(('localhost', 0))
        socket1.listen(5)
        socket2.listen(5)
        self.testNode1.testSocket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.testNode1.testSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.testNode1.testSocket1.connect(socket1.getsockname())
        newSock1, newSock1Addr = socket1.accept()
        self.testNode1.testSocket2.connect(socket2.getsockname())
        newSock2, newSock2Addr = socket2.accept()
        newSock1.settimeout(5)
        newSock2.settimeout(5)
        self.testNode1.connectedNodeDict[1] = self.testNode1.testSocket1
        self.testNode1.connectedNodeDict[2] = self.testNode1.testSocket2
        self.idNum = 4
        
        searchReq1 = {"returnPath":[5, 7, 9], "item":"socks", "id":84}
        
        self.testNode1.passOnSearchRequest(searchReq1)
        
        recvData1 = json.loads(newSock1.recv(4096))
        recvData2 = json.loads(newSock2.recv(4096))
        
        expectedMsg = searchReq1
        expectedMsg["returnPath"].append(4)
        expectedMsg["type"] = "search"
        
        self.assertIn(84, self.testNode1.searchRequestsSentList)
        self.assertIn(84, self.testNode1.searchRequestsReceivedDict)
        self.assertEquals(self.testNode1.searchRequestsReceivedDict[84], [5, 7, 9])
        self.assertEquals(expectedMsg, recvData1)
        self.assertEquals(expectedMsg, recvData2)
        
        searchReq2 = {"returnPath":[5, 7, 1], "item":"socks", "id":76}
        
        self.testNode1.passOnSearchRequest(searchReq2)
        
        self.assertRaises(socket.timeout, newSock1.recv, [4096])
        recvData2 = json.loads(newSock2.recv(4096))
        
        expectedMsg = searchReq2
        expectedMsg["returnPath"].append(4)
        expectedMsg["type"] = "search"
        
        self.assertIn(84, self.testNode1.searchRequestsSentList)
        self.assertIn(84, self.testNode1.searchRequestsReceivedDict)
        self.assertEquals(self.testNode1.searchRequestsReceivedDict[84], [5, 7, 1])
        self.assertEquals(expectedMsg, recvData2)
        
        return
        
if __name__ == "__main__":
    unittest.main()