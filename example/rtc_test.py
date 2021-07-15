# -*- coding: utf-8 -*-
import time
import datetime
from raspi_io.utility import scan_server
from raspi_peri.rtc.ds1302 import DS1302

if __name__ == "__main__":
    i = 100
    print(scan_server(0.05))
    raspberry = scan_server(0.05)[0]
    rtc = DS1302(raspberry=raspberry, timeout=3)
    rtc.write_datetime(datetime.datetime.now())
    while i >= 0:
        i -= 1
        print(rtc.read_datetime())
        time.sleep(0.1)
