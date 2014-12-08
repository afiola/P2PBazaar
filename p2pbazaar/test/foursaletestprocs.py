#import pdb; pdb.set_trace()
import threading
import multiprocessing
from p2pbazaar.tracker import Tracker
from p2pbazaar.buyernode import BuyerNode
from p2pbazaar.sellernode import SellerNode

class TrackerProcess(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self, target=self.main)
        self.stopEvent = multiprocessing.Event()
    
    def main(self):
        tracker = Tracker()
        tracker.startup()
        self.stopEvent.wait()
        tracker.shutdown()
    
    def shutdown(self):
        self.stopEvent.set()
        
class BuyerProcess(multiprocessing.Process):
    def __init__(self, debug=False, itemList = [], shutdownWhenDone=False):
        multiprocessing.Process.__init__(self, target=self.main, args=(debug, itemList, shutdownWhenDone))
        self.stopEvent = multiprocessing.Event()
        self.doneEvent = multiprocessing.Event()
    
    def main(self, debug, itemList, shutdownWhenDone):
        node = BuyerNode(debug, itemList, shutdownWhenDone)
        node.goShopping()
        self.doneEvent.set()
        if not shutdownWhenDone:
            self.stopEvent.wait()
            node.shutdown()
    
    def shutdown(self):
        self.doneEvent.wait()
        self.stopEvent.set()
        
class SellerProcess(multiprocessing.Process):
    def __init__(self, debug = False, itemList=[]):
        multiprocessing.Process.__init__(self, target=self.main, args=(debug, itemList))
        self.stopEvent = multiprocessing.Event()
    
    def main(self, debug, itemList):
        node = SellerNode(debug, itemList)
        node.setUpShop()
        self.stopEvent.wait()
        node.shutdown()
    
    def shutdown(self):
        self.stopEvent.set()

if __name__ == "__main__":
    trackerProc = TrackerProcess()
    trackerProc.start()
    sellerProcList = []
    sellerProcList.append(SellerProcess(debug = True, itemList = ["shoes", "socks", "plutonium"]))
    sellerProcList.append(SellerProcess(debug = True, itemList = ["socks", "plutonium", "Nintendo 64"]))
    for proc in sellerProcList:
        proc.start()
    buyerProcList = []
    buyerProcList.append(BuyerProcess(debug = True, itemList = ["shoes", "plutonium"]))
    buyerProcList.append(BuyerProcess(debug = True, itemList = ["socks", "Nintendo 64"]))
    for proc in buyerProcList:
        proc.start()
        #import pdb; pdb.set_trace()
    for proc in buyerProcList:
        proc.shutdown()
    for proc in sellerProcList:
        proc.shutdown()
    trackerProc.shutdown()