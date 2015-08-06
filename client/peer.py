import socket
import struct

from messages.c2c_pb2 import NFCData, Status, Anticol
from messages.c2s_pb2 import Session, Data
from messages.metaMessage_pb2 import Wrapper
from nfprint import prettyPrintProtobuf

def SocketReadN(sock, n):
    buf = b''
    while n > 0:
        data = sock.recv(n)
        if data == b'':
            raise RuntimeError('unexpected connection close')
        buf += data
        n -= len(data)
    return buf



def getSessionMessage(opcode, errcode=Session.ERROR_NOERROR, secret=None):
    session = Session()
    session.opcode = opcode
    session.errcode = errcode
    if secret is not None:
        session.session_secret = secret
    wrapper = Wrapper()
    wrapper.Session.MergeFrom(session)
    return wrapper

def assertSessionMessageState(msg, opcode, errcode=Session.ERROR_NOERROR):
    assert msg.WhichOneof('message') == 'Session'
    assert msg.Session.opcode == opcode
    assert msg.Session.errcode == errcode

class peer:
    def __init__(self, host="127.0.0.1", port=5566):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def joinSession(self, secret):
        self.secret = secret
        msg = getSessionMessage(Session.SESSION_JOIN, secret=secret)
        reply = self.transceive(msg)
        assertSessionMessageState(reply, Session.SESSION_JOIN_SUCCESS)

    def createSession(self):
        msg = getSessionMessage(Session.SESSION_CREATE)
        reply = self.transceive(msg)
        assertSessionMessageState(reply, Session.SESSION_CREATE_SUCCESS)
        self.secret = reply.Session.session_secret
        return self.secret

    def leaveSession(self):
        self.transceive(getSessionMessage(Session.SESSION_LEAVE, secret=self.secret))

    def close(self):
        self.sock.close()

    def transceive(self, msg):
        self.sendOneMsg(msg)
        return self.RecvOneMsg()

    def sendOneMsg(self, msg):
        mm = msg.SerializeToString()
        self.sock.sendall(struct.pack(">i", len(mm)) + mm)

    def RecvOneMsg(self):
        lengthbuf = SocketReadN(self.sock, 4)
        length = struct.unpack(">i", lengthbuf)[0]
        wrapper = Wrapper()
        wrapper.ParseFromString(SocketReadN(self.sock, length))
        return wrapper

    def sendWrappedData(self, data):
        wrapper = Wrapper()
        d = Data()
        d.errcode = Data.ERROR_NOERROR
        d.blob = data.SerializeToString()
        wrapper.Data.MergeFrom(d)
        self.sendOneMsg(wrapper)

    def transceiveWrappedData(self, data):
        self.sendWrappedData(data)
        msg = self.RecvOneMsg()
        assert msg.WhichOneof('message') == "Data"
        while not msg.Data.blob:
            assert msg.Data.errcode == Data.ERROR_NOERROR
            msg = self.RecvOneMsg()

        wrapper = Wrapper()
        wrapper.ParseFromString(msg.Data.blob)
        #prettyPrintProtobuf(wrapper)
        return wrapper

    def sendAnticol(self, uid, hist, atqa, sak):
        a = Anticol()
        a.UID = uid
        a.historical_byte = hist
        a.ATQA = atqa
        a.SAK = sak
        d = Wrapper()
        d.Anticol.MergeFrom(a)
        self.sendWrappedData(d)

    def sendStatus(self, statuscode):
        s = Status()
        s.code = statuscode
        d = Wrapper()
        d.Status.MergeFrom(s)
        self.sendWrappedData(d)

    def packNfcData(self, data_source, data_bytes):
        n = NFCData()
        n.data_source = data_source
        n.data_bytes = data_bytes
        d = Wrapper()
        d.NFCData.MergeFrom(n)
        return d

    def sendNfcData(self, data_source, data_bytes):
        self.sendWrappedData(self.packNfcData(data_source, data_bytes))

    def transceiveNfcData(self, data_source, data_bytes):
        """
        :rtype : NFCData
        """
        reply = self.transceiveWrappedData(self.packNfcData(data_source, data_bytes))
        assert reply.WhichOneof('message') == "NFCData"
        return reply.NFCData

    def onSocket(self):
        msg = self.RecvOneMsg()
        type = msg.WhichOneof('message')
        if type == "Data":
            wrapper = Wrapper()
            wrapper.ParseFromString(msg.Data.blob)
            prettyPrintProtobuf(wrapper)
            self.onData(wrapper)

    def onData(self, data):
        assert isinstance(data, Wrapper)
        mtype = data.WhichOneof('message')
        if mtype == "Status":
            self.onStatus(data, data.Status.code)
        elif mtype == "Anticol":
            self.onAnticol(data, data.Anticol)
        elif mtype == "NFCData":
            self.onNfcData(data, data.NFCData.data_source, data.NFCData.data_bytes)

    def onStatus(self, data, statuscode):
        assert isinstance(data, Wrapper)

    def onAnticol(self, data, anticol):
        assert isinstance(data, Wrapper)
        assert isinstance(anticol, Anticol)

    def onNfcData(self, data, source, bytes):
        assert isinstance(data, Wrapper)