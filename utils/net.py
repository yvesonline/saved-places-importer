#!/usr/bin/env python2

import socket
from contextlib import closing

def check_socket(host, port):
    """
    Returns True if successful (i.e. host and port reachable), otherwise False.
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as my_sock:
        return my_sock.connect_ex((host, port)) == 0
