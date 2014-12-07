#import pdb; pdb.set_trace()
import threading
from p2pbazaar.tracker import Tracker
from p2pbazaar.buyernode import BuyerNode
from p2pbazaar.sellernode import SellerNode

if __name__ == "__main__":
    
    tracker = Tracker()
    tracker.startup()
    sellerNodeList = []
    sellerNodeList.append(SellerNode(debug = True, itemList = ["shoes", "socks", "plutonium"]))
    sellerNodeList.append(SellerNode(debug = True, itemList = ["socks", "plutonium", "Nintendo 64"]))
    for node in sellerNodeList:
        node.setUpShop()
    buyerNodeList = []
    buyerNodeList.append(BuyerNode(debug = True, itemList = ["shoes", "plutonium"]))
    buyerNodeList.append(BuyerNode(debug = True, itemList = ["socks", "Nintendo 64"]))
    buyerThreadList = []
    for node in buyerNodeList:
        buyerThreadList.append(threading.Thread(target = node.goShopping))
    for thread in buyerThreadList:
        thread.start()
    for node in sellerNodeList:
        node.shutdown()
    tracker.shutdown()