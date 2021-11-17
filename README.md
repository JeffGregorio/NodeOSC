# NodeOSC

Open Sound Control (OSC) messaging via UDP/TCP and device management for ESP8266-based NodeMCU microcontrollers programmed using the Arduino IDE. 

## Application

For wireless control of multimedia systems using NodeMCU-based embedded devices. OSC messages can be sent via UDP implement low-latency wireless controllers (e.g. for musical instruments), or sent via TCP with guaranteed arrival where latency is less critical.

*Note: these IoT devices do not encrypt credentials, as they are intended for controlling multimedia systems on local networks that don't require internet connection or otherwise don't provide access to sensitive data or systems.*

The Arduino example `gate.ino` demonstrates basic NodeOSC device configuration and sends an OSC message to a OSC server when the state of a digital pin changes. Optionally, the pin's state can be requested by an OSC server.

The Max/MSP example `test.maxpat` acts as an OSC server/client, and uses UDP broadcast to obtain IP addresses and device identifiers for any NodeMCU devices listening on the port. 

The example `multi.maxpat` acts as an OSC server/client and demonstrates how networks of multiple NodeOSC devices can be managed using JavaScript within Max/MSP. This system automatically populates a dictionary of IP addresses keyed by the device identifiers, meaning addresses don't have to be hard-coded or configured as static or reserved. 

Both examples can be optionally used with `bridge.py`, a python-based TCP server which maintains reliable connections to NodeOSC devices and relays OSC messages to and from Max/MSP on a localhost UDP port.

## Installation

To use with the Arduino IDE, download this repository as a ZIP and place in your Arduino/libraries directory, likely ~/Documents/Arduino/libraries/ on Mac OS and \My Documents\Arduino\libraries\ on Windows. 

### Dependencies

*Note, the code in this repository was most recently tested using Max 8.1.11 and Arduino 1.8.13 under Mac OS 11.3.*

[ESP8266 package](https://create.arduino.cc/projecthub/electropeak/getting-started-w-nodemcu-esp8266-on-arduino-ide-28184f):

* Open Arduino IDE's preferences and add `http://arduino.esp8266.com/stable/package_esp8266com_index.json` under "Additional Boards Manager URLs" 
* Under Tools > Board > Boards Manager, search for 'esp8266' and install

[ESPAsyncTCP](https://github.com/me-no-dev/ESPAsyncTCP)

## Example Device Configuration and OSC via UDP

### With an NodeMCU
0. Add a 10k pulldown resistor from pin D1 to GND. Connect a momentary pushbutton, switch, or test wire that can be connected to the NodeMCU's 3.3V supply or other logic HIGH source.

### In the Arduino IDE
1. Program a NodeMCU device with the `gate.ino` example sketch and open the serial monitor for debug information. Wait for the device to open an access point. 

### From a desktop or mobile device
2. Find the device's access point as `ap-device-1` in the list of available networks. Connect to it using the password `iotconfig`.
3. Connecting opens a captive portal in which to provide a network SSID and password for the device to connect to. In the portal, the user can also change the default Device ID (`device`), Node ID (`1`), and UDP/TCP port number (`8000`) that the device transmits on. 
4. Submit changes in the portal. The device will close the access point and connect to the WiFi network with the supplied credentials. The onboard LED will blink slowly while connecting, and blink quickly eight times upon a successful connection. 

*Note 1: If connection fails in step 4, the device will re-open as an access point. Repeat steps 2-4, double-checking the WiFi network's SSID, pass, and status.*

*Note 2: The options provided in the portal are saved on the device's flash memory. The next time it is booted it will attempt to connect to the same WiFi network, then open an access point if this fails.*

### In Max/MSP

5. Open `test.maxpat` and open the Max Console.
6. Click on `/ping` to broadcast to any NodeOSC devices. If you changed the device's UDP/TCP port number in step 3, make sure to change the `[udpsend]` object's port number accordingly.
7. Examine the console for a response from the device `/pong device 1 [ip_address] 8000`

*Note: the `gate.ino` example device is configured to send its outgoing OSC messages to the IP address that sent the `/ping` message. This address is saved on the device's flash memory and retrieved at startup.*

*Note: optionally, the message '/config' manually disconnects the device from the WiFi network and re-opens the device's access point.*

### On the NodeMCU
8. Test the example device's main OSC message `/gate` by connecting pin D1 to logic HIGH by the means configured in step 0. The received message will be displayed in the console followed by the device's Node ID and the state of the pin.


## OSC via TCP

While OSC via TCP in Max/MSP is possible using `[mxj net.tcp.recv]` and `[mxj net.tcp.send]`, these objects do not handle messages asynchronously or maintain connections with TCP servers and clients after sending/receiving messages, making bidirectional communication difficult. 

An alternative is possible with the `[sadam.TCPServer]` object available in the [sadam library](https://cycling74.com/tools/the-sadam-library/), but this provides only the raw bytes of OSC messages that have to be decoded into a string format according to the OSC protocol. 

A possibly less demanding alternative for the Python-literate is provided in `bridge.py`, which has a single dependency [python-osc](https://pypi.org/project/python-osc/) that can be easily installed using pip.

1. Install python-osc at the terminal using `pip install python-osc`
2. With the `test.maxpat` open from the previous example, run `bridge.py` at the command line using `python bridge.py [ip_address] 8000 9000`, where `ip_address` is your computer's  address (found in System Preferences > Network in Mac OS and Settings > Network & Internet > Wi-Fi in Windows). 
3. Click `/ping` again so that the NodeOSC device initiates a TCP connection with the Python script. At the terminal, verify the connection was accepted. 
4. In the `text.maxpat` patch, change the IP address argument in the `/tcp` message block at the bottom to the address of the NodeOSC device. 
5. Click the message. This relays the osc message `/state` via TCP to the NodeOSC device. At the terminal and the Arduino Serial Monitor, verify the message was sent and received via TCP. 

## Multiple devices

1. Program multiple NodeOSC devices using the `gate.ino` example and configure them with unique combinations of Device ID and Node ID.
2. Open the Max/MSP patch `multi.maxpat` and open the Max Console.
3. Press `/ping` to broadcast address requests to all connected devices.
4. In the Max Console, verify the `[js devmanager]` block receives the a `/pong` message from each device and creates a dictionary entry.
5. Test dispatching of OSC messages to devices by Device and Node ID using the example messages `/state` and `/config`.

*Note: if the `bridge.py` script is terminated or unused, the `gate.ino` devices will fall back on transmitting via UDP. However, `[js devmanager]` will not transmit to the devices via UDP unless the second argument [bridge port] is removed.*
