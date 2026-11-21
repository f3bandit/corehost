#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 f3bandit. A standalone client of corehost's socket (NOTICE: not covered by corehost's GPL).
# test frontend for corehost: holds the screen and the menu button, logs replies/events, commands from /tmp/chf.in
#   (the socket: /tmp/corehost.sock, or COREHOST_SOCK as corehost itself takes it; it reconnects after each core load)
import socket, os, time, select
SOCK = os.environ.get('COREHOST_SOCK') or '/tmp/corehost.sock'
LOG = open('/tmp/chf.log', 'a', buffering=1)
def log(s): LOG.write('%.1f %s\n' % (time.time() % 10000, s))
if not os.path.exists('/tmp/chf.in'): os.mkfifo('/tmp/chf.in')
fifo = os.open('/tmp/chf.in', os.O_RDWR | os.O_NONBLOCK)
waiting = False
while True:
    try:
        s = socket.socket(socket.AF_UNIX); s.connect(SOCK)
    except OSError:
        if not waiting: log('waiting for corehost on %s' % SOCK); waiting = True
        s.close(); time.sleep(0.3); continue
    waiting = False
    log('connected')
    try:
        for c in ('hello', 'subscribe', 'screen frontend', 'sheet on'): s.sendall((c + '\n').encode())
        buf = b''
        while True:
            r, _, _ = select.select([s, fifo], [], [], 1)
            if fifo in r:
                for c in os.read(fifo, 4096).decode().splitlines():
                    if c.strip(): log('> ' + c); s.sendall((c + '\n').encode())
            if s in r:
                d = s.recv(65536)
                if not d: log('disconnected'); break
                buf += d
                while b'\n' in buf:
                    l, buf = buf.split(b'\n', 1); log('< ' + l.decode('utf-8', 'replace')[:400])
    except OSError as e:          # (corehost went away mid-send: a core loading starts Main again)
        log('disconnected (%s)' % e)
    s.close(); time.sleep(0.3)
