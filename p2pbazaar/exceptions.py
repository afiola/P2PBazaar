class BadConnectionException(Exception):
    def __init__(self, msg, badConnSocket, badConnID = -1):
        self.badSocket = badConnSocket
        self.badID = badConnID
        self.msg = msg
#End of BadConnectionException class.

class BadMessageException(Exception):
    def __init__(self, msg, socket):
        self.socket = socket
        self.msg = msg
#End of BadMessageException class.

class MissingMessageTypeException(Exception):
    def __init__(self, socket):
        self.socket = socket