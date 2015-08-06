from messages.c2c_pb2 import NFCData, Status

NFC_CODES = {
    NFCData.READER: "Reader",
    NFCData.CARD  : "Card"
}

STATUS_CODES = {
    Status.KEEPALIVE_REQ   : "Keepalive request",
    Status.KEEPALIVE_REP   : "Keepalive response",
    Status.CARD_FOUND      : "Card found",
    Status.CARD_REMOVED    : "Card removed",
    Status.READER_FOUND    : "Reader found",
    Status.READER_REMOVED  : "Reader removed",
    Status.NFC_NO_CONN     : "NFC connection lost",
    Status.INVALID_MSG_FMT : "Invalid message format",
    Status.NOT_IMPLEMENTED : "Not implemented",
    Status.UNKNOWN_MESSAGE : "Unknown Message",
    Status.UNKNOWN_ERROR   : "Unknown Error"
}
def prettyPrintProtobuf(msg):
    mtype = msg.WhichOneof('message')
    if mtype == "Status":
        mStatus = msg.Status
        print """Status
    StatusCode: {}""".format(
            STATUS_CODES[mStatus.code]
        )
    elif mtype == "Anticol":
        mAnticol = msg.Anticol
        print """Anticol
    UID:  {}
    Hist: {}
    ATQA: {}
    SAK:  {}""".format(
            ''.join(x.encode('hex') for x in mAnticol.UID),
            ''.join(x.encode('hex') for x in mAnticol.historical_byte),
            ''.join(x.encode('hex') for x in mAnticol.ATQA),
            ''.join(x.encode('hex') for x in mAnticol.SAK)
        )
    elif mtype == "NFCData":
        mNfc = msg.NFCData
        print """NFCData
    DataSource: {}
    data_bytes: {}""".format(
            NFC_CODES[mNfc.data_source],
            strhex(mNfc.data_bytes)
        )
    elif mtype == "Session":
        print mtype

def strhex(str):
    return ''.join(x.encode('hex') for x in str)

def bytehex( byteStr ):
    return ''.join( [ "0x%02X " % ord( x ) for x in byteStr ] ).strip()