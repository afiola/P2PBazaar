#import pdb; pdb.set_trace()
import time
from p2pbazaar.tracker import Tracker
from p2pbazaar.buyernode import BuyerNode
from p2pbazaar.sellernode import SellerNode

if __name__ == "__main__":
    
    startTime = time.time()
    tracker = Tracker(debug = False)
    print tracker.startup()
    #time.sleep(1)
    print "Tracker.startup() done. Time elapsed: {0}s".format(time.time()-startTime)
    sellerNode = SellerNode(debug = False, itemList = ["shoes", "socks", "plutonium"])
    sellerNode.setUpShop()
    #time.sleep(1)
    print "SellerNode.setUpShop() done. Time elapsed: {0}s".format(time.time()-startTime)
    buyerNode = BuyerNode(debug = True, itemList = ["socks"], shutdownWhenDone=True)
    print "BuyerNode init done. Time elapsed: {0}s".format(time.time()-startTime)
    buyerNode.goShopping()
    print "BuyerNode.goShopping() done. Time elapsed: {0}s".format(time.time()-startTime)
    sellerNode.shutdown()
    tracker.shutdown()
    print "All shutdowns done. Time elapsed: {0}s".format(time.time()-startTime)