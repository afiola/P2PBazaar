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
        return
        
        
        
if __name__ == "__main__":
    unittest.main()