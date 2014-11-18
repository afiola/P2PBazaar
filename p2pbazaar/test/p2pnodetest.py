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
        
class JoinNetworkTestCase(P2PNodeTest):
    def runTest(self):
        mockNodeListenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        mockNodeListenSocket.bind(('localhost',0))
        mockNodeListenPort = mockNodeListenSocket.getsockname()[1]
        self.mockTrackerListenSocket.settimeout(5)
        self.testNode1.joinNetwork(inHostname = 'localhost', inPort = trackerPort)
        testNodeTrackerSock, testNodeAddr = self.mockTrackerListenSocket.accept()
        assertIsNotNone(testNodeTrackerSock)
        
        recvData = json.loads(testNodeTrackerSock.recv(4096))
        assertIn("type", recvData)
        assertEquals(recvData["type"], "thisisme")
        assertIn("port", recvData)
        assertEquals(recvData["port"], self.testNode1.listenSocket.getsockname()[1])
        
        idMsg = json.dumps({"type":"thisisyou","id":1337})
        testNodeTrackerSock.send(idMsg)
        time.sleep(1)
        assertEquals(self.testNode1.idNum, 1337)
        
        recvData = json.loads(testNodeTrackerSock.recv(4096))
        assertIn("type", recvData)
        assertEquals(recvData["type"], "nodereq")
        
        nodeRepMsg = json.dumps({"type":"nodereply", "id":9001, "port":mockNodeListenPort})
        testNodeTrackerSock.send(nodeRepMsg)
        mockNodeListenSocket.settimeout(5)
        mockNodeDirectSock, mockNodeSockAddr = mockNodeListenSocket.accept()
        mockNodeDirectSock.settimeout(5)
        recvData = json.loads(mockNodeDirectSock.recv(4096))
        assertIn("type", recvData)
        assertEquals(recvData["type"], "thisisme")
        assertIn("id", recvData)
        assertEquals(recvData["id"], 1337)
        
       
        
        mockNodeListenSocket.shutdown(socket.SHUT_RDWR)
        mockNodeListenSocket.close()
        
if __name__ == "__main__":
    unittest.main()