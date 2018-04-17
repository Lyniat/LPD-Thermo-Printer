#!/usr/bin/env python

import logging
from zeroconf import ServiceInfo, Zeroconf, DNSOutgoing

import socket
import time
import os
import sys
from PIL import Image, ImageFile
from thread import start_new_thread
import json

import thermo

class Server:

    CONF_FILE = './conf.json'

    TEMP_FILE = ''
    CONVERTED_FILE = ''

    WIDTH = 0
    HEIGHT = 0

    QUALITY = 1 #starting at 1

    PRINTER_IP = ''
    PRINTER_PORT = 0

    waiting = False

    '''
        load configuration file which can also be configured for your needs
    '''
    def loadConf(self):
        try:
            conf = json.load(open(self.CONF_FILE))

            self.TEMP_FILE = conf["files"]["temp"]
            self.CONVERTED_FILE = conf["files"]["converted"]

            self.WIDTH = conf["image"]["width"]
            self.HEIGHT = conf["image"]["height"]
            self.QUALITY = conf["image"]["quality"]

            self.PRINTER_IP = conf["printer"]["ip"]
            self.PRINTER_PORT = conf["printer"]["port"]
        except:
            print "FAILED LOADING CONFIGURATION FILE"
            sys.exit()

    '''
        the postscript driver writes "%%BoundingBox:" with values to the end of the file
        but PIL can not convert the ps document if "%%BoundingBox:" has no values at the beginning
        this fix writes the values from the last "%%BoundingBox:" to the first one
    '''
    def fixBoundingBox(self):
        #read file
        with open(self.TEMP_FILE, 'r') as file:
            content = file.read()

        #change bounding box
        lines = content.split("\n")

        beginning = 0
        ending = len(lines) -1

        while True:
            line = lines[beginning]
            if "%%BoundingBox:" in line:
                break
            else:
                beginning += 1

        while True:
            line = lines[ending]
            if "%%BoundingBox:" in line:
                break
            else:
                ending -= 1

        lines[beginning] = lines[ending]

        changed = "\n".join(lines)

        #delete old file
        try:
            os.remove(self.TEMP_FILE)
        except OSError:
            pass

        #write to new file
        f = open(self.TEMP_FILE, 'wb')
        f.write(changed)
        f.close()

    '''
        converts ps file to png and sends image to upload script
    '''
    def convert(self):
        print("fixing image")
        self.fixBoundingBox() #PIL has problem with eps bounding box if not fixed
        print("starting converting image")

        image = Image.open(self.TEMP_FILE)
        image.load(scale=self.QUALITY)
        width = 384
        #height = int(384.0 / im.size[0] * im.size[1]) #480
        wpercent = (width/float(image.size[0]))
        height = int((float(image.size[1])*float(wpercent)))
        image = image.resize((width,height), Image.NEAREST)
        image.save(self.CONVERTED_FILE)

        try:
            os.remove(self.TEMP_FILE)
        except OSError:
            pass

        print("finished converting image")
        #sys.exit()


        #com_2_7.upload(self.CONVERTED_FILE)
        
        thermo.print_image()

    '''
        hosts the server which simulates an lpd printer
    '''

    def host(self):
        print("started server")
        try:
            os.remove(self.TEMP_FILE)
        except OSError:
            pass

        ZERO = bytearray([0x00])

        PACKET_SIZE = 1024

        count = 0

        mySocket = socket.socket()
        mySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mySocket.bind((self.PRINTER_IP, self.PRINTER_PORT))

        mySocket.listen(1)
        conn, addr = mySocket.accept()
        print ("Connection from: " + str(addr))
        while True:
            try:
                data = conn.recv(PACKET_SIZE)

                print ("count: "+str(count))

                if not data:
                    #break
                    #print("no data")
                    time.sleep(0.001)
                else:
                    print ("from connected  user with length "+str(len(data)))
                    if count >= 4:
                        f = open(self.TEMP_FILE, 'ab')
                        f.write(data.encode())
                        f.close()

                        if len(data) != PACKET_SIZE: #chance 1/PACKET_SIZE to fail
                            conn.sendall(ZERO)
                            conn.close()
                        #toFile(data)
                    else:
                        print (data)
                        time.sleep(0.5)
                        conn.sendall(ZERO)
                    #time.sleep(1)

                    count += 1
            except:
                print ("no connection")
                if count > 0:
                    break



        self.convert()
        sys.exit()

        try:
            os.remove(self.CONVERTED_FILE)
        except OSError:
            pass

    '''
        starts and hosts the zeroconf service and restarts if it crashes
    '''
    def hostZeroConf(self):
        while(True):
            try:
                self.zeroConf()
            except:
                print("Zeroconf failed. Starting again")
            yield

    '''
        host zeroconf service, so that printer can be found in network
        see: https://en.wikipedia.org/wiki/Zero-configuration_networking
    '''
    def zeroConf(self):
        print("starting zeroconf")
        logging.basicConfig(level=logging.DEBUG)

        desc = {}

        info = ServiceInfo("_printer._tcp.local.",
                           "e-Paper._printer._tcp.local.",
                           socket.inet_aton(self.PRINTER_IP), self.PRINTER_PORT, 0, 0,
                           desc, "ash-2.local.")

        zeroconf = Zeroconf()
        zeroconf.register_service(info)
        print("zeroconf registered device")


'''
    program entry point
    starts lpd socket
    and zeroconf server in a new thread
'''
if __name__ == '__main__':
    print("started application")

    server = Server()

    server.loadConf()

    start_new_thread(server.zeroConf,())

    while True:
        if server.waiting == False:
            #try:
                server.host()
           # except:
               # print("LPD Server failed. Starting again")
