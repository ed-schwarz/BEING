import socket # for socket 
import sys 
import pyvisa
import os
import platform    # For getting the operating system name
import subprocess  # For executing a shell command


def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Option for the number of packets as a function of
    param = '-n' if platform.system().lower()=='windows' else '-c'

    # Building the command. Ex: "ping -c 1 google.com"
    command = ['ping', param, '1', host]

    return subprocess.call(command) == 0

def get_constants(prefix):
    """Create a dictionary mapping socket module constants to their names."""
    return dict( (getattr(socket, n), n)
                 for n in dir(socket)
                 if n.startswith(prefix)
                 )

def connect_to_s_test(ip):
    HOST = ip  # Standard loopback interface address (localhost)
    PORT = 5024  # Port to listen on (non-privileged ports are > 1023)
    server_address = (HOST, PORT)
    sock = socket.create_connection(server_address)
    return sock

def send_to_s_test(sock, data):
    sock.send(data)

def read_from_s_test(sock):
    return sock.recv(1024)

families = get_constants('AF_')
types = get_constants('SOCK_')
protocols = get_constants('IPPROTO_')

ping('192.168.1.77')

HOST = '192.168.1.77'  # Standard loopback interface address (localhost)
#HOST = 'localhost'




sock = connect_to_s_test(HOST)

sock.close()



