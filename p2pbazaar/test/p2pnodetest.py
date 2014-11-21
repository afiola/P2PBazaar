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
        
class TrackerConnectTestCase(P2PNodeTest):
    def awaitMessageThread(self, **kwargs):
        event = kwargs["event"]
        id = kwargs["newID"]
        event.set()
        testNodeTrackerSock, testNodeAddr = self.mockTrackerListenSocket.accept()
        recvData = json.loads(testNodeTrackerSock.recv(4096))
        assertIn("type", recvData)
        assertEquals(recvData["type"], "thisisme")
        assertIn("port", recvData)
        msg = json.dumps({"type":"thisisyou", "id":id})
        testNodeTrackerSock.send(msg)
        return
        
    
    def runTest(self):
        newID = 4000
        event = threading.Event()
        thread = threading.Thread(target = self.awaitMessageThread, kwargs={"event":event, "newID":newID})
        thread.run()
        event.wait()
        assertTrue(self.testNode1.trackerConnect(trackerPort))
        return
        
        
if __name__ == "__main__":
    unittest.main()