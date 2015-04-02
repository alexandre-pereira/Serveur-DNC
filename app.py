# coding: utf-8
import socket
import sys
from client import Client
from logger import Logger
import ConfigParser

config = ConfigParser.ConfigParser()
config.read("dncserver.conf")

Logger.initialiser(config.get("Configuration", "Logfile"))
PORT = int(config.get("Configuration", "Port"))

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error, msg:
    print("Could not create socket. Error Code: ", str(msg[0]), "Error: ", msg[1])
    sys.exit(0)
try:
    s.bind(('', PORT))
except socket.error, msg:
    print("Bind Failed. Error Code: {} Error: {}".format(str(msg[0]), msg[1]))
    sys.exit()

s.listen(50)
Logger.logger.info("Serveur lancé")

while True:
    conn, addr = s.accept()
    print("Connecte a " + addr[0] + ":" + str(addr[1]))
    c = Client(conn)


s.close()
