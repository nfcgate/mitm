
import select

def mainloop(a_peers):
    peers = { }
    for p in a_peers:
        peers[p.sock] = p

    while 1:
        r,w,e = select.select(peers.keys(), [], [])
        for sock in r:
            peers[sock].onSocket()
