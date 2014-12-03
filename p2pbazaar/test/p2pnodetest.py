import socket
import threading
import unittest
import json
import time
from p2pbazaar.p2pnode import P2PNode
from p2pbazaar import trackerPort
from p2pbazaar.test import mocks

class P2PNodeTest(unittest.TestCase):
    def setUp(self):
        self.testNode = P2PNode()
        self.trackerThread = threading.Thread(target=self.trackerFunc)
        self.nodeThread = threading.Thread(target=self.nodeFunc)
        self.trackerEvent = threading.Event()
        self.nodeEvent = threading.Event()
        
    def trackerFunc(self):
        self.mockTracker = mocks.MockTracker()
        self.trackerEvent.set()
        self.mockTracker.accept()
    
    def nodeFunc(self):
        self.mockNode = mocks.MockNode(id = 2001)
        self.nodeEvent.set()
        self.mockNode.accept()
       
    def tearDown(self):
        self.testNode.shutdown()
        del self.testNode
        
class StartupTest(P2PNodeTest):
    def setUp(self):
        P2PNodeTest.setUp(self)
        self.mockNode = mocks.MockNode(port = 1000)
    
    def runTest(self):
        self.assertTrue(self.testNode.startup())
        targetPort = self.testNode.listenSocket.getsockname()[1]
        self.mockNode.connect(port = targetPort)
        msg = json.dumps({"type":"ping"})
        self.mockNode.sendToNode(msg)
        
    def tearDown(self):
        P2PNodeTest.tearDown(self)
        self.mockNode.nodeSocket.shutdown(socket.SHUT_RDWR)
        self.mockNode.nodeSocket.close()
        del self.mockNode
        
class TrackerConnectTest(P2PNodeTest):
    def setUp(self):
        P2PNodeTest.setUp(self)
        self.trackerThread.start()
        
    def trackerFunc(self):
        P2PNodeTest.trackerFunc(self)
        msg = self.mockTracker.receiveDict()
        self.assertIn("type", msg)
        self.assertEquals(msg["type"], "thisisme")
        self.assertIn("port", msg)
        self.assertEquals(msg["port"], self.testNode.listenSocket.getsockname()[1])
        self.mockTracker.sendTIY(1000)
        self.trackerEvent.set()
    
    def runTest(self):
        self.trackerEvent.wait(5)
        self.trackerEvent.clear()
        self.assertTrue(self.testNode.trackerConnect())
        self.assertTrue(self.waitEvent.wait(5))
        return
        
        
class RequestNodeTest(P2PNodeTest):
    def setUp(self):
        P2PNodeTest.setUp(self)
        self.trackerThread.start()
    
    def trackerFunc(self):
        P2PNodeTest.trackerFunc(self)
        msg = self.mockTracker.receiveDict()
        self.mockTracker.sendTIY(1000)
        self.trackerEvent.set()
        msg = self.mockTracker.receiveDict()
        self.assertIn("type", msg)
        self.assertEquals(msg["type"], "nodereq")
        self.assertIn("idList", msg)
        self.assertIn(1000, msg["idList"])
        self.trackerEvent.set()
    
    def runTest(self):
        self.trackerEvent.wait(5)
        self.trackerEvent.clear()
        self.testNode.trackerConnect()
        self.assertTrue(self.trackerEvent.wait(5))
        self.trackerEvent.clear()
        self.assertTrue(self.testNode.requestOtherNode())
        self.assertTrue(self.trackerEvent.wait(5))
        return
        
class ConnectNodeTest(P2PNodeTest):
    def setUp(self):
        P2PNodeTest.setUp(self)
        self.nodeThread.start()
        
    def nodeFunc(self):
        P2PNodeTest.nodeFunc(self)
        msg = self.mockNode.receiveDict()
        self.assertIn("type", msg)
        self.assertEquals(msg["type"], "thisisme")
        self.assertIn("id", msg)
        self.assertEquals(msg["id"], self.testNode.idNum)
        self.assertIn("port", msg)
        self.assertEquals(msg["port"], self.testNode.listenSocket.getsockname()[1])
        self.nodeEvent.set()
        
    def runTest(self):
        self.nodeEvent.wait(5)
        self.nodeEvent.clear()
        self.assertTrue(self.testNode.connectNode(otherID = 2001, otherNodePort = self.mockNode.listenPort))
        self.nodeEvent.wait(5)
        self.nodeEvent.clear()
        self.assertIn(2001, self.testNode.connectedNodeDict)
        
class DisconnectNodeTest(P2PNodeTest):
    def setUp(self):
        P2PNodeTest.setUp(self)
        self.nodeThread.start()
    
    def nodeFunc(self):
        P2PNodeTest.nodeFunc(self)
        msg = self.mockNode.receiveDict()
        self.nodeEvent.set()
        msg = self.mockNode.receiveDict()
        self.assertIn("type", msg)
        self.assertEquals(msg["type"], "dc")
        self.nodeEvent.set()
        
    def runTest(self):
        self.nodeEvent.wait(5)
        self.nodeEvent.clear()
        self.testNode.connectNode(otherID = 2001, otherNodePort = self.mockNode.listenPort)
        self.nodeEvent.wait(5)
        self.nodeEvent.clear()
        self.testNode.disconnectNode(otherID = 2001)
        self.nodeEvent.wait(5)
        time.sleep(2)
        self.assertNotIn(2001, self.testNode.connectedNodeDict)
        


class HandleReceivedTrackerTest(P2PNodeTest):
    def setUp(self):
        P2PNodeTest.setUp(self)
        self.nodeThread.start()
        self.mockTrackerThread = mocks.MockThread()
        self.testNode.trackerThread = self.mockTrackerThread
        
    def runTest(self):
        
        #Test ThisIsYou
        msg = json.dumps({"type":"thisisyou"})
        self.assertTrue(self.testNode.handleReceivedTracker(inPacketData = msg))
        
        #Test ping
        msg = json.dumps({"type":"ping"})
        self.assertTrue(self.testNode.handleReceivedTracker(inPacketData = msg))
        
        #Test error
        msg = json.dumps({"type":"error"})
        self.assertTrue(self.testNode.handleReceivedTracker(inPacketData = msg))
        
        #Test node reply
        msg = json.dumps({"type":"nodereply"})
        self.assertTrue(self.testNode.handleReceivedTracker(inPacketData = msg))
        
        #Test unrecognized message
        msg = json.dumps({"type":"lolwat"})
        self.assertFalse(self.testNode.handleReceivedTracker(inPacketData = msg))
        
        return
        
class HandleReceivedNodeTest(P2PNodeTest):
    def setUp(self):
        P2PNodeTest.setUp(self)
        self.mockNodeThread = mocks.MockThread()

    def runTest(self):
        thread = self.mockNodeThread
        
        #Test ping
        msg = json.dumps({"type":"ping"})
        self.assertTrue(self.testNode.handleReceivedNode(inPacketData = msg, connectThread = thread))
        
        #Test ThisIsMe
        msg = json.dumps({"type":"thisisme"})
        self.assertTrue(self.testNode.handleReceivedNode(inPacketData = msg, connectThread = thread))
        
        #Test error
        msg = json.dumps({"type":"error"})
        self.assertTrue(self.testNode.handleReceivedNode(inPacketData = msg, connectThread = thread))
        
        #Test disconnect
        msg = json.dumps({"type":"dc"})
        self.assertTrue(self.testNode.handleReceivedNode(inPacketData = msg, connectThread = thread))
        
        #Test search
        msg = json.dumps({"type":"search"})
        self.assertTrue(self.testNode.handleReceivedNode(inPacketData = msg, connectThread = thread))
        
        return
        
class PassOnSearchTest(P2PNodeTest):
    def runTest(self):
        mockNodeList=[mocks.MockNode(id = (n + 2001)) for n in range(3)]
        for node in mockNodeList:
            self.testNode.connectNode(node.idNum, node.listenPort)
            node.accept()
        recvData = [mockNodeList[n].receiveDict() for n in range(3)]
        
        searchReq1 = {"type":"search", "returnPath":[5, 7, 9], "item":"socks", "id":84}
        
        self.assertEquals(self.testNode.passOnSearchRequest(searchReq1), [2001, 2002, 2003])
        
        recvData = [mockNodeList[n].receiveDict() for n in range(3)]
        
        expectedMsg = searchReq1
        
        self.assertIn(84, self.testNode.searchRequestsSentList)
        self.assertIn(84, self.testNode.searchRequestsReceivedDict)
        self.assertEquals(self.testNode.searchRequestsReceivedDict[84], [5, 7, 9, self.testNode.idNum])
        for data in recvData:
            self.assertEquals(data, expectedMsg)
        
        searchReq2 = {"type":"search", "returnPath":[5, 7, 2001], "item":"socks", "id":76}
        expectedMsg = searchReq2
        
        self.testNode.passOnSearchRequest(searchReq2)
        
        self.assertRaises(socket.timeout, mockNodeList[0].receiveDict())
        recvData2 = [mockNodeList[n].receiveDict() for n in range(1,3)]
        
        
        self.assertIn(76, self.testNode.searchRequestsSentList)
        self.assertIn(76, self.testNode.searchRequestsReceivedDict)
        self.assertEquals(self.testNode.searchRequestsReceivedDict[76], [5, 7, 2001, self.testNode1.idNum])
        self.assertEquals(expectedMsg, recvData2[0])
        self.assertEquals(expectedMsg, recvData2[1])
        
        return
        
class ShutdownTest(P2PNodeTest):
    def runTest(self):
        self.testNode.shutdown()
        self.assertTrue(self.testNode.shutdownFlag)
        
class MakeTIMTest(P2PNodeTest):
    def runTest(self):
        self.testNode.startup()
        expectedMSG = json.dumps({"type":"thisisme", "port":self.testNode.listenSocket.getsockname()[1], "id":self.testNode.idNum})
        self.assertEquals(self.testNode._makeTIM(), expectedMSG)
        
class MakePingTest(P2PNodeTest):
    def runTest(self):
        expectedMSG = json.dumps({"type":"ping"})
        self.assertEquals(self.testNode._makePing(), expectedMSG)
        
class MakeSearchReqTest(P2PNodeTest):
    def runTest(self):
        inMsg = {"returnPath":[]}
        expectedMSG = json.dumps({"returnPath":[self.testNode.idNum]})
        self.assertEquals(self.testNode._makeSearchReq(inMsg), expectedMSG)
        
class MakeDCTest(P2PNodeTest):
    def runTest(self):
        expectedMSG = json.dumps({"type":"dc"})
        self.assertEquals(self.testNode._makeDC(), expectedMSG)
        
class MakeNodeReqTest(P2PNodeTest):
    def runTest(self):
        self.testNode.connectedNodeDict[2] = " "
        expectedMSG = json.dumps({"type":"nodereq", "idList":[2]})
        self.assertEquals(self.testNode._makeNodeReq(), expectedMSG)
        
class MakeErrorTest(P2PNodeTest):
    def runTest(self):
        expectedMSG = json.dumps({"type":"error", "code":"bleh"})
        self.assertEquals(self.testNode._makeError(errorCode = "bleh"), expectedMSG)
        expectedMSG = json.dumps({"type":"error", "code":"bleh", "info":"Nothing in particular"})
        self.assertEquals(self.testNode._makeError(errorCode = "bleh", readableMsg = "Nothing in particular"), expectedMSG)
        
class HandleTIMTest(P2PNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
        self.testNode.connectedNodeDict[2001] = mockThread
        
        data = {}
        self.assertFalse(self.testNode._handleTIM(inData = data, connectThread = mockThread))
        
        data = {"id":2001}
        self.assertFalse(self.testNode._handleTIM(inData = data, connectThread = mockThread))
        
        data = {"id":2002}
        self.assertTrue(self.testNode._handleTIM(inData = data, connectThread = mockThread))
        self.assertNotIn(2001, self.testNode.connectedNodeDict)
        self.assertIn(2002, self.testNode.connectedNodeDict)
        self.assertIs(self.testNode.connectedNodeDict[2002], mockThread)
        self.assertTrue(mockThread.connectedEvent.isSet())
        
class HandleTIYTest(P2PNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
        self.testNode.idNum = 2001
        
        data = {"id":40}
        self.assertFalse(self.testNode._handleTIY(data, mockThread))
        self.assertEquals(self.testNode.idNum, 2001)
        self.assertFalse(mockThread.connectEvent.isSet())
        
        self.testNode.trackerThread = mockThread
        data = {}
        self.assertFalse(self.testNode._handleTIY(data, mockThread))
        self.assertEquals(self.testNode.idNum, 2001)
        self.assertFalse(mockThread.connectEvent.isSet())
        
        data = {"id":-1}
        self.assertFalse(self.testNode._handleTIY(data, mockThread))
        self.assertEquals(self.testNode.idNum, 2001)
        self.assertFalse(mockThread.connectEvent.isSet())
        
        data = {"id":40}
        self.assertTrue(self.testNode._handleTIY(data, mockThread))
        self.assertEquals(self.testNode.idNum, 40)
        self.assertTrue(mockThread.connectEvent.isSet())
        
class HandlePingTest(P2PNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
        mockThread.expectingPing = True
        self.assertFalse(self.testNode._handlePing(mockThread))
        self.assertFalse(mockThread.expectingPing)
        
        self.assertTrue(self.testNode._handlePing(mockThread))
        expectedMsg = json.dumps({"type":"ping"})
        self.assertEquals(mockThread.sentMsg, expectedMsg)
    
class HandleErrorTest(P2PNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
        
        data = {}
        self.assertEquals(self.testNode._handleError(data, mockThread), ("Bad message", None))
        self.assertIsNone(mockThread.sentMsg)
        
        data = {"code":"lolwat"}
        self.assertEquals(self.testNode._handleError(data, mockThread), ("Unrecognized message", None))
        self.assertIsNone(mockThread.sentMsg)
        
        data = {"code":"notim"}
        self.assertEquals(self.testNode._handleError(data, mockThread), ("notim", None))
        self.assertEquals(mockThread.sentMsg, self.testNode._makeTIM())
        
class HandleDCTest(P2PNodeTest):
    def runTest(self):
        mockThread = mocks.MockThread()
        self.testNode._handleDC(mockThread)
        self.assertTrue(mockThread.shutdownFlag)
        
class HandleSearchTest(P2PNodeTest):
    def runTest(self):
        data = {}
        self.assertFalse(self.testNode._handleSearch(data))
        
        data = {"id":3}
        self.assertFalse(self.testNode._handleSearch(data))
        
        data = {"returnPath":[]}
        self.assertFalse(self.testNode._handleSearch(data))
        
        data = {"id":3, "returnPath":[]}
        self.assertTrue(self.testNode._handleSearch(data))
        
class HandleNodeReplyTest(P2PNodeTest):
    def runTest(self):
        data = {}
        mockThread = mocks.MockThread()
        self.testNode.trackerThread = mockThread
        self.assertFalse(self.testNode._handleNodeReply(data))
        
        data = {"id":2001, "port":1001}
        self.assertFalse(self.testNode._handleNodeReply(data))
        
        data = {}
        mockThread.expectingNodeReply = True
        self.assertFalse(self.testNode._handleNodeReply(data))
        self.assertTrue(mockThread.expectingNodeReply)
        
        self.nodeThread.start()
        self.nodeEvent.wait(5)
        data = {"id":self.mockNode.idNum, "port":self.mockNode.listenPort}
        self.assertTrue(self.testNode._handleNodeReply(data))
        self.assertFalse(mockThread.expectingNodeReply)
        
if __name__ == "__main__":
    unittest.main()