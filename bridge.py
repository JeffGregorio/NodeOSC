import threading
import warnings
import socket
import selectors
import types
import asyncore
import argparse

from pythonosc import osc_server
from pythonosc import dispatcher
from pythonosc import osc_message_builder

# -----------------------------
# UDP Client (sends to Max/MSP)
# -----------------------------
class UDPClient:

	def __init__(self, addr):
		if addr[0] is None:
			self._addr = (socket.gethostbyname(socket.gethostname()), addr[1])
		else:
			self._addr = addr
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self._sock.setblocking(0)
		self.print_helper("Created")
		return

	def print_helper(self, description, addr=None, data=None, nl=False):
		print('') if nl else None
		print("UDPClient %15s:%5d:" % self._addr, end=' ')
		print("%12s" % description, end=' ')
		print("%s:%d" % addr, end='') if addr else None
		print("%a" % data, end='') if data else None
		print(' ')
		return

	def send(self, data):
		# self.print_helper("Data out:", data=data)
		self._sock.sendto(data, self._addr)
		return

# --------------------------------------
# OSC-UDP Server (receives from Max/MSP)
# --------------------------------------
class OSCServer:

	def __init__(self, addr, default_handler=None):
		if addr[0] is None:
			self._addr = (socket.gethostbyname(socket.gethostname()), addr[1])
		else:
			self._addr = addr
		try:
			self._dispat = dispatcher.Dispatcher()
			self._server = osc_server.ThreadingOSCUDPServer(self._addr, self._dispat)
			self.print_helper("Created")
		except OSError:
			self.print_helper("Port in use")
		if default_handler:
			self._dispat.set_default_handler(default_handler, False)
		return

	def print_helper(self, description, addr=None, data=None):
		print("OSCServer %15s:%5d:" % self._addr, end=' ')
		print("%12s" % description, end=' ')
		print("%s:%d" % addr, end='') if addr else None
		print(":%a" % data, end='') if data else None
		print(' ')
		return

	def dispatch(self, path, handler, args=None):
		if not args:
			self._dispat.map(path, handler)
		else:
			self._dispat.map(path, handler, args)
		return

	def begin(self):			
		try:
			threading.Thread(target=self._server.serve_forever, daemon=True).start()
			self.print_helper("Listening")
		except AttributeError:
			print("%s.%s(): No server port specified" % (type(self).__name__, self._server.__name__ ))
		return

	def shutdown(self):
		try:
			self._server.shutdown()
			self._server.server_close()
		except AttributeError:
			print("%s.%s(): No server available" % (type(self).__name__, self._server.__name__ ))
		return

# --------------------------
# TCP Client for IoT devices
# --------------------------
class TCPClient(asyncore.dispatcher_with_send):

	def __init__(self, addr, *args, **kwargs):
		super(TCPClient, self).__init__(*args, **kwargs)
		self._addr = addr
		self._data_handler = None
		return

	def print_helper(self, description, addr=None, data=None, nl=False):
		print('') if nl else None
		print("TCPClient %15s:%5d:" % self._addr, end=' ')
		print("%12s" % description, end=' ')
		print("%s:%d" % addr, end='') if addr else None
		print("%a" % data, end='') if data else None
		print(' ')
		return

	def set_data_handler(self, handler):
		self._data_handler = handler
		return

	def handle_accept(self):
		pair = self.accept()
		if pair is not None:
			sock, addr = pair
			self.print_helper("Accepted", addr=addr)
			return

	def handle_read(self):
		data = self.recv(1024)
		# self.print_helper("Data in:", data=data, nl=True)
		if data and self._data_handler:
			self._data_handler(self, data)
		else:
			self.close()
		return

	def handle_close(self):
		self.print_helper("Disconnected")
		self.close()
		return

	def hendle_error(self):
		self.print_helper("Error")
		self.error()
		return

	def send(self, data):
		self.print_helper("Data out:", data=data)
		super(TCPClient, self).send(data)
		return

# -----------------------------------------------
# TCP Server (sends/receives to/from IoT devices)
# -----------------------------------------------
class TCPServer(asyncore.dispatcher):

	def __init__(self, addr):
		asyncore.dispatcher.__init__(self)
		if addr[0] is None:
			self._addr = (socket.gethostbyname(socket.gethostname()), addr[1])
		else:
			self._addr = addr
		self._clients = {}
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.set_reuse_addr()
		self.bind(self._addr)
		self.print_helper("Created")
		return

	def print_helper(self, description, addr=None):
		print("TCPServer %15s:%5d:" % self._addr, end=' ')
		print("%12s" % description, end=' ')
		print("%s:%d" % addr) if addr else print(' ')
		return

	def begin(self):
		self.listen(5)
		self.print_helper("Listening")
		return

	def set_data_handler(self, handler):
		self._data_handler = handler
		return

	def handle_accept(self):
		pair = self.accept()
		if pair is not None:
			sock, addr = pair
			self.print_helper("Accepted", addr)
			self._clients[addr[0]] = TCPClient(addr, sock)
			self._clients[addr[0]].set_data_handler(self._data_handler)
		return

	def handle_read(self):
		data = self.recv(1024)
		# self.print_helper("Data in:", ("???", 0))
		return

	def handle_close(self):
		self.print_helper("Closing", self._addr)
		self.close()
		return

	def hendle_error(self):
		self.print_helper("Error")
		self.error()
		return

if __name__ == "__main__":

	# Relay TCP messages from NodeOSC devices to Max/MSP on localhost via UDP
	def handle_tcp_to_udp(tcp_client, data):
		print("-- Routing OSC Message: (TCP) %s:%d" % tcp_client._addr, end=' ')
		print("--> (UDP) %s:%d" % to_max._addr)
		to_max.send(data)	

	# Translate OSC-UDP messages from Max/MSP with /tcp path
	def handle_udp_to_tcp(addr, *args):

		if len(args) < 3:
			print("Invalid /tcp message...\n")
			print("	Usage: /tcp [dest_addr] [dest_port] [/oscpath] [arg1] ... [argN]\n")
			return

		# Get the destination TCP client
		dest_addr = args[0]
		dest_port = args[1]
		
		# Make an OSC message with the third argument as the path
		builder = osc_message_builder.OscMessageBuilder(args[2])
		if (len(args) > 3):
			[builder.add_arg(val) for val in args[3:]]
		msg = builder.build()

		# Retrieve the TCP client with the specified IP
		try:
			tcp_client = tcp_server._clients[dest_addr]
		except:
			print("\nNo TCP Client %s:%d" % tcp_client._addr)

		# Send the message
		try:
			print("-- Routing OSC Message: (UDP) %s:%d" % from_max._addr, end=' ')
			print("--> (TCP) %s:%d" % tcp_client._addr)
			tcp_client.send(msg.dgram)
		except:
			print("\nFailed to send to TCP client %s:%d" % tcp_client._addr)
		
		return	

	# Create parser for command line arguments
	parser = argparse.ArgumentParser(
		description='Precompute wave/parameter tables')

	# Public IP address
	parser.add_argument('ip_addr',
		type=str,
		help='Public IP Address')

	# Iot Device Port
	parser.add_argument('iot_port', 
		type=int,
		default=8000, 
		help='UDP/TCP port for IoT devices')
	
	# Max/MSP Port
	parser.add_argument('max_port', 
		type=int,
		default=9000, 
		help='UDP port for Python <---> Max/MSP')

	# Args
	args = parser.parse_args()

	# OSC-UDP client (e.g. Max/MSP) --> Local OSC-UDP server --> TCP Clients
	from_max = OSCServer(('localhost', args.max_port))
	from_max.dispatch('/tcp', handle_udp_to_tcp)

	# TCP Clients --> TCP Server --> Local UDP Client (e.g. Max/MSP)
	tcp_server = TCPServer((args.ip_addr, args.iot_port))
	tcp_server.set_data_handler(handle_tcp_to_udp)
	to_max = UDPClient(('localhost', args.iot_port))

	# Go
	print('')
	from_max.begin()
	tcp_server.begin()
	asyncore.loop()

