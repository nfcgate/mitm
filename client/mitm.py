from client.desfire import desfire
from client.nfprint import strhex
from client.peer import peer
from messages.c2c_pb2 import NFCData, Status


class mitmpeer(peer):

    def __init__(self, host="127.0.0.1", port=5566):
        peer.__init__(self, host, port)
        self.side = None
        self.lastAPDU = None

    def setMitm(self, mitm):
        self.mitm = mitm

    def setOtherPeer(self, peer):
        self.otherpeer = peer

    def onStatus(self, data, statuscode):
        if statuscode == Status.CARD_FOUND:
            self.side = NFCData.CARD
            self.mitm.cardpeer = self
        elif statuscode == Status.READER_FOUND:
            self.side = NFCData.READER
            self.mitm.readerpeer = self
        self.mitm.onStatus(self.side, self, self.otherpeer, data, statuscode)

    def onAnticol(self, data, anticol):
        self.mitm.onAnticol(self.side, self, self.otherpeer, data, anticol)

    def onNfcData(self, data, source, bytes):
        self.lastAPDU = bytes
        if self.side == NFCData.CARD:
            self.mitm.backlog.append((self.otherpeer.lastAPDU, self.lastAPDU))

        self.mitm.onNfcData(self.side, self, self.otherpeer, data, bytes)

class mitm:

    cardpeer = None
    readerpeer = None

    def __init__(self):
        self.backlog = []

    def onStatus(self, srcname, srcpeer, otherpeer, data, statuscode):
        otherpeer.sendStatus(statuscode)

    def onAnticol(self, srcname, srcpeer, otherpeer, data, anticol):
        otherpeer.sendAnticol(anticol.UID, anticol.historical_byte, anticol.ATQA, anticol.SAK)
        return

    def onNfcData(self, srcname, srcpeer, otherpeer, data, bytes):
        otherpeer.sendNfcData(srcname, bytes)
        return

    def getLastBacklog(self, requestAPDU):
        for t in self.backlog:
            if t(0)[0:len(requestAPDU)] == requestAPDU:
                return t

class dfmitm(mitm):

    inAuthPhase = False
    lastRequestAPDU = ""
    selectedAID = ""

    def __init__(self):
        mitm.__init__(self)

    def onNfcData(self, srcname, srcpeer, otherpeer, data, bytes):
        def relay(): otherpeer.sendNfcData(srcname, bytes)
        relay()
        if srcname == NFCData.READER:
            print "lastRequestAPDU -> " + strhex(bytes)
            self.lastRequestAPDU = bytes
        else:
            cmd = self.lastRequestAPDU[0]
            reply = bytes[0]
            cmdOk = reply == desfire.RESPONSE_OK

            if cmd == desfire.CMD_SELECT and cmdOk:
                print "cmd: CMD_SELECT"
                self.selectedAID = self.lastRequestAPDU[1:]
                self.onAidSelected(self.lastRequestAPDU[1:])
            elif cmd == desfire.CMD_AUTH and reply == desfire.CMD_AUTHPHASE:
                print "cmd: CMD_AUTH"
                self.inAuthPhase = True
                self.onAuthStart()
            elif cmd == desfire.CMD_AUTHPHASE and reply == desfire.RESPONSE_OK:
                print "cmd: CMD_AUTHPHASE"
                self.inAuthPhase = False
                self.onAuthenticated()


        return

    def onAidSelected(self, aid):
        return
    def onAuthStart(self):
        return
    def onAuthenticated(self):
        return


def createPeers(mitm, host="127.0.0.1", port=5566):

    peer1 = mitmpeer(host, port)
    peer2 = mitmpeer(host, port)
    peer1.setOtherPeer(peer2)
    peer1.setMitm(mitm)
    peer2.setOtherPeer(peer1)
    peer2.setMitm(mitm)
    return [peer1, peer2]







