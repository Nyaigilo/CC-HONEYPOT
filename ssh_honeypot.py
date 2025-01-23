#libraries
import logging
from logging.handlers import RotatingFileHandler
import socket
import paramiko
import threading
#constants
logging_format = logging.Formatter('%(message)s')
SSH_BANNER = "SSH-2.0-Paramiko-Server v1.0.0"
#host_key = 'server.key'
host_key = paramiko.RSAKey(filename='server.key')
#loggers and loging files
funnel_logger = logging.getLogger('FunnelLogger')
funnel_logger.setLevel(logging.INFO)
funnel_handler =  RotatingFileHandler('audits.log',maxBytes=2000, backupCount=5)
funnel_handler.setFormatter(logging_format)
funnel_logger.addHandler(funnel_handler)

creds_logger = logging.getLogger('CredsLogger')
creds_logger.setLevel(logging.INFO)
creds_handler =  RotatingFileHandler('cmd_audits.log',maxBytes=2000, backupCount=5)
creds_handler.setFormatter(logging_format)
creds_logger.addHandler(creds_handler)
#emmulate shell
def emulated_shell(channel, client_ip):
    channel.send(b'corporate-jumpbox2$')
    command = b""
    
    while True:
        char = channel.recv(1)
        if not char:
            channel.close()
            break

        command += char  # Add each received character to the command buffer
        
        if char == b'\r':  # If Enter is pressed, execute the command
            if command.strip() == b'exit':
                response = b'\nGOOD BYE?\n'
                channel.send(response)
                channel.close()
                break  # Exit the loop after sending the goodbye message
            elif command.strip() == b'pwd':
                response = b'\n\\usr\\local\\' + b'\r\n'
                creds_logger.info(f'Command {command.strip()}' + 'executed by ' + f'{client_ip}')
            elif command.strip() == b'whoami':
                response = b'corpuser1' + b'\r\n'
                creds_logger.info(f'Command {command.strip()}' + 'executed by ' + f'{client_ip}')
            elif command.strip() == b'ls':
                response = b'jumpbox1.config' + b'\r\n'
                creds_logger.info(f'Command {command.strip()}' + 'executed by ' + f'{client_ip}')
            elif command.strip() == b'cat jumpbox.config':
                response = b'go to noster.com' + b'\r\n'
                creds_logger.info(f'Command {command.strip()}' + 'executed by ' + f'{client_ip}')
            else:
                response = b'\n' + bytes(command.strip()) + b'\r\n'
                creds_logger.info(f'Command {command.strip()}' + 'executed by ' + f'{client_ip}')
            
            # Send the response and reset the command buffer for the next input
            channel.send(response)
            channel.send(b'corporate-jumpbox2$')
            command = b""  # Clear the command buffer

#SSHserver sockets
class Server(paramiko.ServerInterface):

    def __init__(self, client_ip, input_username = None, input_password = None):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.input_username = input_username
        self.input_password = input_password

    def check_channel_request(self, kind: str, chanid: int) -> int:
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        
    def get_allowed_auths(self, username):
        return "password"
    
    def check_auth_password(self, username, password):
        funnel_logger.info(f'Client {self.client_ip} attempted connection with' + f'username:{username},' + f'password')
        creds_logger.info(f'{self.client_ip}, {username}, {password}')
        if self.input_username is not None and self.input_password is not None:
            if username ==self.input_username and password ==self.input_password:
                return paramiko.AUTH_SUCCESSFUL
            else:
                return paramiko.AUTH_FAILED
        else:
            return paramiko.AUTH_SUCCESSFUL
            
    def check_channel_shell_request(self, channel):
        self.event.set()
        return True
    
    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
    
    def check_channel_exec_request(self, channel, command):
        command = str(command)
        return True
    
def client_handle(client, addr, username, password):
    client_ip = addr[0]
    print(f"{client_ip} has connected to the server")


    try:


        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        server = Server(client_ip=client_ip, input_username=username, input_password=password)

        transport.add_server_key(host_key)

        transport.start_server(server=server)

        channel = transport.accept(100)
        if channel is None:
            print("no channel was opened.")
        else:
        
         standard_banner = "Welcome to Ubuntu 22.04 lts"
         channel.send(standard_banner)
        emulated_shell(channel,client_ip=client_ip)


    except Exception as error:
        print(error)
        print("||| error |||")
    
    finally:
        try:
            if transport:
             transport.close()
        except Exception as error:
            print(error)
            print("||| error |||")
        client.close()
        
#provision SSH_BASED HONEYPOT
def honeypot(address, port, username, password):

    socks =socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    socks.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    socks.bind((address,port))

    socks.listen(100)
    print(f"SSH server is listening on port {port}.")

    while True:
        try:
            client, addr = socks.accept()
            ssh_honeypot_thread = threading.Thread(target=client_handle, args=(client, addr, username,password))
            ssh_honeypot_thread.start()
        except Exception as error:
            print(error)

honeypot('127.0.0.1', 2223, username = None, password = None)