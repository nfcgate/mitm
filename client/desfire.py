import struct
from client.nfprint import strhex, bytehex
from messages.c2c_pb2 import NFCData

FILE_STANDARD = '\x00'
FILE_BACKUP   = '\x01'
FILE_VALUE    = '\x02'
FILE_LINEAR   = '\x03'
FILE_CYCLIC   = '\x04'

ENCRYPTION_PLAIN    = '\x00'
ENCRYPTION_MAC      = '\x01'
ENCRYPTION_CIPHERED = '\x03'

class desfire:
    CMD_SELECT ="\x5A"
    CMD_AUTH = "\xAA"
    CMD_AUTHPHASE = "\xAF"
    CMD_READ_FILE = "\xBD"
    CMD_READ_VALUE = "\x6C"

    RESPONSE_OK = "\x00"
    def __init__(self, peer):
        """
        :type peer: peer
        """
        self.peer = peer

    def trans(self, bytes):
        return self.peer.transceiveNfcData(NFCData.READER, bytes).data_bytes

    def selectAid(self, aid):
        return self.trans("\x5A" + aid)

    def readFile(self, id):
        return self.trans("\xBD" + id + "\x00\x00\x00\x20\x00\x00")

    def printFile(self, fid):
        reply = self.readFile(fid)
        print "File " + strhex(fid) + ": " + strhex(reply)

    def readValue(self, fid):
        reply = self.trans("\x6C" + fid)
        if reply[0] == "\x00":
            return self.parseAsInt(reply[1:5])
        else:
            raise Exception("invalid reply in readValue()")

    def DebitDecrease(self, fid, debit):
        return self.trans("\xDC" + fid + self.intToBytes(debit))

    def CreditIncrease(self, fid, credit):
        return self.trans("\x0C" + fid + self.intToBytes(credit))

    def getFileIDs(self):
        reply = self.trans("\x6F")
        if (reply[0] == "\x00"):
            return reply[1:]
        else:
            return []

    def intToBytes(self, i):
        return struct.pack('I', i)
    def bytesToInt(self, b):
        return struct.unpack('I', b)

    def parseAsInt(self, bytes):
        return int(bytes[::-1].encode('hex'), 16)

    def getFileSettings(self, fileno):
        def parseAccessByte(access):
            if access == 14:
                return "Free"
            elif access == 15:
                return "Denied"
            else:
                return "Key " + str(access)

        reply = self.trans("\xf5" + fileno)
        if reply[0] == "\x00":
            fileSettings = {'fileNo': fileno}

            # Parse File type
            fileSettings["type_byte"] = reply[1]
            if fileSettings["type_byte"] == FILE_STANDARD:
                fileSettings["type"] = "Standard Data File"
            elif fileSettings["type_byte"] == FILE_BACKUP:
                fileSettings["type"] = "Backup Data File"
            elif fileSettings["type_byte"] == FILE_VALUE:
                fileSettings["type"] = "Value File with Backup"
            elif fileSettings["type_byte"] == FILE_LINEAR:
                fileSettings["type"] = "Linear Record with Backup"
            elif fileSettings["type_byte"] == FILE_CYCLIC:
                fileSettings["type"] = "Cyclic Record with Backup"
            else:
                fileSettings["type"] = "Unknown"

            # Parse Encryption Mode
            fileSettings["encmode_byte"] = reply[2]
            if fileSettings["encmode_byte"] == ENCRYPTION_PLAIN:
                fileSettings["encmode"] = "Plain"
            elif fileSettings["encmode_byte"] == ENCRYPTION_MAC:
                fileSettings["encmode"] = "Plain + MAC"
            elif fileSettings["encmode_byte"] == ENCRYPTION_CIPHERED:
                fileSettings["encmode"] = "Enciphered"
            else:
                fileSettings["encmode"] = "Unknown"

            # Parse Access Control
            fileSettings["read_byte"]  = (int(reply[4].encode('hex'), 16) >> 4) & 15 # 15 == \x0F => Last 4 bits
            fileSettings["write_byte"] =  int(reply[4].encode('hex'), 16)       & 15
            fileSettings["rw_byte"]    = (int(reply[3].encode('hex'), 16) >> 4) & 15
            fileSettings["admin_byte"] =  int(reply[3].encode('hex'), 16)       & 15

            fileSettings["read"]  = parseAccessByte(fileSettings["read_byte"])
            fileSettings["write"] = parseAccessByte(fileSettings["write_byte"])
            fileSettings["rw"]    = parseAccessByte(fileSettings["rw_byte"])
            fileSettings["admin"] = parseAccessByte(fileSettings["admin_byte"])

            # Parse extra information
            if fileSettings["type_byte"] in [FILE_STANDARD, FILE_BACKUP]:
                fileSettings["userFileSize"]     = self.parseAsInt(reply[5:8])
            elif fileSettings["type_byte"] == FILE_VALUE:
                fileSettings["minCredit"]        = self.parseAsInt(reply[13:17])
                fileSettings["maxCredit"]        = self.parseAsInt(reply[9:13])
                fileSettings["maxLtdCredit"]     = self.parseAsInt(reply[5:9])
            elif fileSettings["type_byte"] in [FILE_LINEAR, FILE_CYCLIC]:
                fileSettings["currentRecords"]   = self.parseAsInt(reply[5:8])
                fileSettings["maxRecords"]       = self.parseAsInt(reply[8:11])
                fileSettings["singleRecordSize"] = self.parseAsInt(reply[11:14])

            return fileSettings
        else:
            return None

    def printFileSettings(self, fileSettings):
        print "File Settings for FileNo " + bytehex(fileSettings["fileNo"])
        if fileSettings["type"] != "Unknown":
            print "  type:               " + fileSettings["type"]
        else:
            print "  type:               Unknown (" + bytehex(fileSettings["type_byte"]) + ")"

        if fileSettings["encmode"] != "Unknown":
            print "  Encryption Mode:    " + fileSettings["encmode"]
        else:
            print "  Encryption Mode:    Unknown (" + bytehex(fileSettings["encmode_byte"]) + ")"

        print "  Access (R):         " + fileSettings["read"]
        print "  Access (W):         " + fileSettings["write"]
        print "  Access (RW):        " + fileSettings["rw"]
        print "  Access (Change):    " + fileSettings["admin"]

        if fileSettings["type_byte"] in ['\x00', '\x01']:
            print "  User File Size:     " + str(fileSettings["userFileSize"])
        elif fileSettings["type_byte"] == '\x02':
            print "  Min Credit:         " + str(fileSettings["minCredit"])
            print "  Max Credit:         " + str(fileSettings["maxCredit"])
            print "  Max Limited Credit: " + str(fileSettings["maxLtdCredit"])
        elif fileSettings["type_byte"] in ['\x03', '\x04']:
            print "  Current Records:    " + str(fileSettings["currentRecords"])
            print "  Max Records:        " + str(fileSettings["maxRecords"])
            print "  Single Record Size: " + str(fileSettings["singleRecordSize"])
