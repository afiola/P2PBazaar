#import pdb; pdb.set_trace()
import time
from p2pbazaar.tracker import Tracker
from p2pbazaar.buyernode import BuyerNode
from p2pbazaar.sellernode import SellerNode

if __name__ == "__main__":
    
    tracker = Tracker(debug = True)
    tracker.startup()
    #time.sleep(1)
    sellerNode = SellerNode(debug = True, itemList = ["shoes", "socks", "plutonium"])
    sellerNode.setUpShop()
    #time.sleep(1)
    buyerNode = BuyerNode(debug = True, itemList = ["socks"])
    buyerNode.goShopping()
    sellerNode.shutdown()
    tracker.shutdown()