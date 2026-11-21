#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 f3bandit. A standalone client of corehost's socket (NOTICE: not covered by corehost's GPL).
# ch.py command [command ...]: send commands to corehost, print each reply
#   (the socket: /tmp/corehost.sock, or COREHOST_SOCK as corehost itself takes it)
import os, socket, sys
SOCK = os.environ.get('COREHOST_SOCK') or '/tmp/corehost.sock'
if len(sys.argv) < 2:
    sys.exit('ch.py command [command ...]   e.g. ch.py hello status')
try:
    s = socket.socket(socket.AF_UNIX); s.settimeout(5); s.connect(SOCK)
except OSError as e:
    sys.exit('corehost is not running (%s: %s): MiSTer_corehost must be the Main running' % (SOCK, e.strerror))
for c in sys.argv[1:]:
    s.sendall((c + '\n').encode()); b = b''
    try:
        while not b.endswith(b'\n'):
            d = s.recv(65536)
            if not d:
                sys.exit('%s -> corehost closed the connection (a core loading starts Main again)' % c)
            b += d
    except socket.timeout:
        sys.exit('%s -> no reply in 5 s' % c)
    print(c, '->', b.decode('utf-8', 'replace').strip()[:600])
