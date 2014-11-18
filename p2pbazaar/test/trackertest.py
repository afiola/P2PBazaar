import json
import unittest
import socket
import random
import time

from threading import ThreadError
from p2pbazaar import trackerPort
from .. import tracker

class TrackerTest(unittest.TestCase):
    
    def setUp(self):
        random.seed()
        self.testTracker = tracker.Tracker(inPort = trackerPort, inDebug = True, inTestMode = True)
        self.testSocket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.testSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket1.bind(('127.0.0.1', 0))
        self.listenSocket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket2.bind(('127.0.0.1', 0))
        self.listenPort1 = self.listenSocket1.getsockname()[1]
        self.listenPort2 = self.listenSocket2.getsockname()[1]
        self.testSocket1.settimeout(10)
        self.testSocket2.settimeout(10)
        self.testTracker.startup()
        
    def tearDown(self):
        try:
            self.testTracker.connectLock.release()
        except ThreadError:
            pass
        try:
            self.testSocket1.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.testSocket1.close()    
        try:
            self.testSocket2.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.testSocket2.close()
        for currentThread in self.testTracker.connThreadList:
            #print "Waiting for thread \"{0}\" to finish...".format(currentThread.name) 
            currentThread.join()
        if self.testTracker.listenThread != None:
            #print "Waiting for tracker listener thread to finish..."
            self.testTracker.listenThread.join()
        
        self.testTracker.listenSocket
        del self.testSocket1
        del self.testSocket2
        del self.testTracker
        self.listenSocket1.close()
        del self.listenSocket1
        self.listenSocket2.close()
        del self.listenSocket2
        self.id1 = -1
        self.id2 = -1
        
class TrackerInitTestCase(TrackerTest):
    def runTest(self):
        #print "Start of TrackerInitTestCase"
        self.assertIsNotNone(self.testTracker.activeNodeDict)
        self.assertIsNotNone(self.testTracker.connectLock)
        #print "End of TrackerInitTestCase"
    
class ListenLoopTestCase(TrackerTest):
    def runTest(self):
        #print "Start of ListenLoopTestCase"
        self.testTracker.connectLock.acquire()
        self.testTracker.connectLock.release()
        self.assertIsNotNone(self.testTracker.listenSocket)
        self.assertEquals(self.testTracker.listenSocket.getsockname()[1], trackerPort)
        self.testSocket1.connect(('127.0.0.1', trackerPort))
        outMessage = json.dumps({"type":"thisisme", "port":self.listenPort1})
        self.testSocket1.send(outMessage)
        recvdata = json.loads(self.testSocket1.recv(4096).decode('utf-8'))
        self.assertIn("type", recvdata)
        self.assertEquals(recvdata["type"], "thisisyou")
        self.assertIn("id", recvdata)
        self.id1 = recvdata["id"]
        #print "ListenLoop test: testSocket1 ID is {0}".format(self.id1)
        self.assertIn(self.id1, self.testTracker.activeNodeDict)
        self.assertEquals(self.listenPort1, self.testTracker.activeNodeDict[self.id1]["port"])
        self.testSocket2.connect(('127.0.0.1', trackerPort))
        outMessage = json.dumps({"type":"thisisme", "port":self.listenPort2})
        self.testSocket2.send(outMessage)
        recvdata = json.loads(self.testSocket2.recv(4096).decode('utf-8'))
        self.assertIn("type", recvdata)
        self.assertEquals(recvdata["type"], "thisisyou")
        self.assertIn("id", recvdata)
        self.id2 = recvdata["id"]
        #print "ListenLoop test: testSocket2 ID is {0}".format(self.id2)
        self.assertIn(self.id2, self.testTracker.activeNodeDict)
        self.assertEquals(self.listenPort2, self.testTracker.activeNodeDict[self.id2]["port"])
        self.assertIn(self.id1, self.testTracker.activeNodeDict)
        self.assertEquals(self.listenPort1, self.testTracker.activeNodeDict[self.id1]["port"])
        #print "End of ListenLoopTestCase"
        
class HandleReceivedTestCase(TrackerTest):
    def runTest(self):
        #print "Start of HandleReceivedTestCase"
        self.testTracker.connectLock.acquire()
        self.testTracker.connectLock.release()
        #Establish connection normally.
        self.testSocket1.connect(('127.0.0.1', trackerPort))
        connectID = json.dumps({"type":"thisisme", "port":self.listenPort1})
        self.testSocket1.send(connectID)
        recvdata = json.loads(self.testSocket1.recv(4096).decode('utf-8'))

        self.id1 = recvdata["id"]
        #print "handleReceived test: testSocket1 ID is {0}".format(self.id1)
        
        #Test sending bad message.
        self.testSocket1.send("lololol")
        #print "handleReceived: sent bad message"
        recvdata = json.loads(self.testSocket1.recv(4096).decode('utf-8'))
        self.assertEquals(recvdata["type"], "error")
        self.assertEquals(recvdata["code"], "wtf")
        #print "handleReceived bad message done"
        
        #Test sending a message that nodes would recognize but the tracker doesn't.
        junkData = json.dumps({"type":"buyOK"})
        self.testSocket1.send (junkData)
        recvdata = json.loads(self.testSocket1.recv(4096).decode('utf-8'))
        self.assertEquals(recvdata["type"], "error")
        self.assertEquals(recvdata["code"], "wtf")
        #print "handleReceived unrecognized message type done"
        
        #Test sending a message of unrecognized type.
        junkData = json.dumps({"type":"whargarbl"})
        self.testSocket1.send(junkData)
        recvdata = json.loads(self.testSocket1.recv(4096).decode('utf-8'))
        self.assertEquals(recvdata["type"], "error")
        self.assertEquals(recvdata["code"], "wtf")
        #print "handleReceived bad message type done"
        
        #Test sending a ThisIsMe with an invalid (negative) port.
        junkData = json.dumps({"type":"thisisme", "port":-20})
        self.testSocket1.send(junkData)
        recvdata = json.loads(self.testSocket1.recv(4096).decode('utf-8'))
        self.assertEquals(recvdata["type"], "error")
        self.assertEquals(recvdata["code"], "wtf")
        #print "handleReceived negative port done"
        
        #Test sending a ThisIsMe with an invalid (string) port.
        junkData = json.dumps({"type":"thisisme", "port":"whargarbl"})
        self.testSocket1.send(junkData)
        recvdata = json.loads(self.testSocket1.recv(4096).decode('utf-8'))
        self.assertEquals(recvdata["type"], "error")
        self.assertEquals(recvdata["code"], "wtf")
        #print "handleReceived string port done"
        
        #Establish a second connection.
        self.testSocket2.connect(('127.0.0.1', trackerPort))
        connectID = json.dumps({"type":"thisisme", "port":self.listenPort2})
        self.testSocket2.send(connectID)
        recvdata = json.loads(self.testSocket2.recv(4096).decode('utf-8'))
        self.id2 = recvdata["id"]
        #print "handleReceived test: testSocket2 ID is {0}".format(self.id2)
        
        #Test sending a ThisIsMe with a new port.
        newID = json.dumps({"type":"thisisme", "port":20000})
        self.testSocket1.send(newID)
        time.sleep(1)
        self.testTracker.connectLock.acquire()
        self.assertEquals(20000, self.testTracker.activeNodeDict[self.id1]['port'])
        self.testTracker.connectLock.release()
        
        #Test sending a NodeRequest message (expecting the new port)
        reqMessage = json.dumps({"type":"nodereq"})
        self.testSocket2.send(reqMessage)
        nodeReply = json.loads(self.testSocket2.recv(4096).decode('utf-8'))
        self.assertIn("type", nodeReply)
        self.assertEquals(nodeReply["type"], "nodereply")
        self.assertIn("id", nodeReply)
        self.assertEquals(nodeReply["id"], self.id1)
        self.assertIn("port", nodeReply)
        self.assertEquals(nodeReply["port"], 20000)
        
        #Test changing to the original port and sending another NodeRequest.
        newID = json.dumps({"type":"thisisme", "port":self.listenPort1})
        self.testSocket1.send(newID)
        time.sleep(1)
        self.testTracker.connectLock.acquire()
        self.testTracker.connectLock.release()
        reqMessage = json.dumps({"type":"nodereq"})
        self.testSocket2.send(reqMessage)
        nodeReply = json.loads(self.testSocket2.recv(4096).decode('utf-8'))
        self.assertEquals(nodeReply["type"], "nodereply")
        self.assertEquals(nodeReply["id"], self.id1)
        self.assertEquals(nodeReply["port"], self.listenPort1)
        
        #Test pings!
        pingMsg = json.dumps({"type":"ping"})
        self.testSocket2.send(pingMsg)
        pingReply = json.loads(self.testSocket2.recv(4096).decode('utf-8'))
        self.assertIn("type", pingReply)
        self.assertEquals(pingReply["type"], "ping")
        pingReply = None
        self.testSocket2.settimeout(20)
        pingReply = json.loads(self.testSocket2.recv(4096).decode('utf-8'))
        self.assertEquals(pingReply["type"], "ping")
        #print "End of HandleReceivedTestCase"
        
        

#end TrackerTest class

def runTrackerTest():
    unittest.main()
    
if __name__ == "__main__":
    unittest.main()
    
    
    
    