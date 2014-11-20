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
        
class RequestOtherNodeTestCase(P2PNodeTest):
    def runTest(self):
        self.testNode1.trackerSocket.connect(('localhost', trackerPort))
        testNodeTrackerSock, testNodeAddr = self.mockTrackerListenSocket.accept()
        msg = json.dumps({"type":"nodereply", "id":9001, "port":1337})
        testNodeTrackerSock.send(msg)
        assertEquals(self.testNode1.requestOtherNode(), {"id":9001, "port":1337})
        
        
if __name__ == "__main__":
    unittest.main()