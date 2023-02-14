import sys
import socket
import selectors
import traceback
from typing import Tuple
import types
from collections import defaultdict
from _thread import *
import threading
from utils import *

sel = selectors.DefaultSelector()
# maintain a dictionary of messages
messages = defaultdict(list)
messages["eric"] = ["hello my love"]
threads = []

host = "127.0.0.1"
port = 22067

# keeps track of all registered users
registeredUsers = set()
# mapping from user to connected socket; also serves as a directory of online users
userToSocket = dict()

def service_connection(sock):
    try:
        while True:
            # read 50 bytes for the command
            command = sock.recv(1)
            command = int.from_bytes(command, "big")
            print(f"client issues command {command}")
            if command == 0:
                username = sock.recv(50).decode('utf-8')
                if username in registeredUsers:
                    # msg = f"the username {username} is already registered. please login"
                    errcode = USERNAME_EXISTS
                else:
                    registeredUsers.add(username)
                    errcode = REGISTRATION_OK
                    # sock.sendall(bytes(msg, 'utf-8'))
            # wait for the user to input a username and map it to the current socket
            elif command == 1:
                # username lengths are limited to 50 bytes
                username = sock.recv(50).decode('utf-8')
                if username in registeredUsers:
                    # print(f"welcome back {username}")
                    if username in userToSocket:
                        errcode = ALREADY_LOGGED_IN
                        # msg = f"the user {username} has already logged in another terminal window"
                    else:
                        # register the socket under the current user's username
                        userToSocket[username] = sock
                        # on login we deliver all undelivered messages
                        numUndelivered = len(messages[username])
                        sock.sendall(bytes(msg, 'utf-8'))
                        if numUndelivered > 0:
                            errcode = LOGIN_OK_UNREAD_MSG
                            msg = f"you have {numUndelivered} unread messages"
                            msg += "".join(messages[username]), 'utf-8'
                            # clear the cache
                            messages[username] = []
                        else:
                            errcode = LOGIN_OK_NO_UNREAD_MSG
                else:
                    errcode = NOT_REGISTERED
                    # msg = f"the username {username} is not in the system. please register before logging in"
                    # sock.sendall(bytes(msg, 'utf-8'))
                    msg = username
            # this means the command is actually a message that is being sent
            elif command == 2:
                # TODO: change the # bytes here
                message = sock.recv(1024).decode('utf-8').split("|")
                sender, recipient, msg = message[0], message[1], message[2]
                # check if the recipient is logged in, and if so deliver instantaneously
                if recipient in userToSocket:
                    err = RECEIVED_INSTANT_OK
                    userToSocket[recipient].sendall(
                        SENT_INSTANT_OK.to_bytes(1, "big") +
                        bytes(f"{sender}|{msg}", 'utf-8')
                    )
                # otherwise, store the message
                else:
                    err = SENT_CACHED_OK
                    messages[recipient].append(f"{sender}|{msg}")
            elif command == "logout":
                userToLogout = sock.recv(50).decode('utf-8')
                err = LOGOUT_OK
                del userToSocket[userToLogout]
            elif command == "delete":
                userToDelete = sock.recv(50).decode('utf-8')
                # if the user is connected via the socket they are calling delete from we can delete their account
                err = DELETE_OK
                del userToSocket[userToDelete]
                del registeredUsers[userToDelete]
            else:
                # we should never get here
                print("error in the command")
    except:
        

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((host, port))
print("socket binded to port", port)

# put the socket into listening mode
sock.listen(5)
print("socket is listening")

try:
    # a forever loop until client wants to exit
    while True:
        # establish connection with client
        c, addr = sock.accept()      
        print('Connected to :', addr[0], ':', addr[1])

        # Start a new thread and return its identifier
        t = start_new_thread(service_connection, (c,))
        threads.append(t)
except KeyboardInterrupt:
    print("keyboard interrupt closing")
    for c in userToSocket.values:
        c.shutdown(socket.SHUT_RDWR)
        c.close()
    sock.close()