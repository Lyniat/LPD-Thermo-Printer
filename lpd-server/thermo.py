#!/usr/bin/env python

from PIL import Image, ImageOps
import sys

import usb.core
import usb.util
import time

class find_class(object):
    def __init__(self, class_):
        self._class = class_
    def __call__(self, device):
        # first, let's check the device
        if device.bDeviceClass == self._class:
            return True
        # ok, transverse all devices to find an
        # interface that matches our class
        for cfg in device:
            # find_descriptor: what's it?
            intf = usb.util.find_descriptor(
                                        cfg,
                                        bInterfaceClass=self._class
                                )
            if intf is not None:
                return True

        return False

def print_image():

    print("python running")
    sys.stdout.flush()

    im = Image.open("./converted.png")
    # remove alpha because inverting does not work with RGBA
    im = im.convert("RGB")
    width = 384
    #height = int(384.0 / im.size[0] * im.size[1]) #480
    wpercent = (width/float(im.size[0]))
    height = int((float(im.size[1])*float(wpercent)))
    print (width, height)
    im = im.resize((width, height),Image.NEAREST)
    print (im.size)
    im = ImageOps.invert(im)
    im = im.convert("1")
    s = im.tobytes()

    im.save("converted.png")

    printers = usb.core.find(find_all=1, custom_match=find_class(7))

    printer_list = list(printers)

    #print("printers",printer_list)

    if len(printer_list) < 1:
        print("Found no Thermo Printer!")
        sys.stdout.flush()

    print("found printer")
    dev = printer_list[0]

    tryagain = True

    while tryagain:

        reattach = False
        if dev.is_kernel_driver_active(0):
            reattach = True
            dev.detach_kernel_driver(0)
            time.sleep(1)

        try:
            dev.set_configuration()

        except:
            #time.sleep(3)
            pass
                
        tryagain = False

    print("after try again")
    # get an endpoint instance
    cfg = dev.get_active_configuration()
    intf = cfg[(0,0)]

    ep = usb.util.find_descriptor(
        intf,
        # match the first OUT endpoint
        custom_match = \
        lambda e: \
            usb.util.endpoint_direction(e.bEndpointAddress) == \
            usb.util.ENDPOINT_OUT)

    assert ep is not None

    PREFIX = "\x1b\x67\x30"
    MODE_UNENCODED = "\x1b\x6d\x00"
    LINE_FEED = "\x1b\x46\x00\xa0"
    BACK_FEED = "\x1b\x5c\x00\xa0"

    '''
    if len(sys.argv) < 2:
        print("Usage: %s <graphics file>" % sys.argv[0])
        sys.stdout.flush()
        sys.exit(0)
    '''

    #printer.write(MODE_UNENCODED)

    print("start printing")

    for i in range(height):
        line = s[int(i*width/8):int((i+1)*width/8)]
        ep.write(PREFIX)
        ep.write(line)
        print ("write",i)

    ep.write(LINE_FEED)

    print ("finished")
