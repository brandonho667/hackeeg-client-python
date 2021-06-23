#!/usr/bin/env python

# Notes:
# To capture at 16,000 samples per second,
# the Arduino Due driver's SPI DMA must be on,
# and the driver communication mode must be set to MessagePack
# (--messagepack option)

import argparse
import uuid
import time
import sys
import select
import threading
import queue
from multiprocessing import Process, Queue, Value


from pylsl import StreamInfo, StreamOutlet

import hackeeg
from hackeeg import ads1299
from hackeeg.driver import SPEEDS, GAINS, Status

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
import numpy as np
import time

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 50000


class HackEegTestApplicationException(Exception):
    pass


class NonBlockingConsole(object):

    def __enter__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, type, value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

    def init(self):
        import tty
        import termios

    def get_data(self):
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return False


class WindowsNonBlockingConsole(object):
    # def init(self):
    #     import msvcrt

    # def get_data(self):
    #     if msvcrt.kbhit():
    #         char = msvcrt.getch()
    #         return char
    #     return False

    def __init__(self):
        self.serial_port = None

    def init(self, serial_port=None):
        self.serial_port = serial_port

    def get_data(self):
        if self.serial_port.in_waiting > 0:
            return self.serial_port.read(1)
        return False


class HackEegTestApplication:
    """HackEEG commandline tool."""

    def __init__(self):
        self.serial_port_name = None
        self.hackeeg = None
        self.channel_test = False
        self.hex = False
        self.messagepack = False
        self.channels = 8
        self.gain = 1
        self.lsl = False
        self.lsl_info = None
        self.lsl_outlet = None
        self.lsl_stream_name = "HackEEG"
        self.stream_id = str(uuid.uuid4())
        self.read_samples_continuously = True
        self.continuous_mode = False
        self.graph_step = 0
        self.start_time = -1
        self.data_process = None
        self.connector = Queue()
        self.pause_toggle = False
        self.dataMatrix = [[],[],[],[],[],[],[],[],[]] # initialize data matrix to RAM

        self.samples_per_second = 0
        self.gain = 0
        self.fileName = ""
        self.debug = False


        print(f"platform: {sys.platform}")
        if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
            self.non_blocking_console = NonBlockingConsole()
        elif sys.platform == "win32":
            self.non_blocking_console = WindowsNonBlockingConsole()
        self.non_blocking_console.init()
        # self.debug = True

    def read_keyboard_input(self):
        char = self.non_blocking_console.get_data()
        if char:
            self.read_samples_continuously = False

    def setup(self, samples_per_second=500, gain=1, messagepack=False):
        if samples_per_second not in SPEEDS.keys():
            raise HackEegTestApplicationException("{} is not a valid speed; valid speeds are {}".format(
                samples_per_second, sorted(SPEEDS.keys())))
        if gain not in GAINS.keys():
            raise HackEegTestApplicationException("{} is not a valid gain; valid gains are {}".format(
                gain, sorted(GAINS.keys())))

        self.hackeeg.stop_and_sdatac_messagepack()
        self.hackeeg.sdatac()
        self.hackeeg.blink_board_led()
        sample_mode = SPEEDS[samples_per_second] | ads1299.CONFIG1_const
        self.hackeeg.wreg(ads1299.CONFIG1, sample_mode)

        gain_setting = GAINS[gain]

        self.hackeeg.disable_all_channels()
        if self.channel_test:
            self.channel_config_test()
        else:
            self.channel_config_input(gain_setting)


        # Route reference electrode to SRB1: JP8:1-2, JP7:NC (not connected)
        # use this with humans to reduce noise
        #self.hackeeg.wreg(ads1299.MISC1, ads1299.SRB1 | ads1299.MISC1_const)

        # Single-ended mode - setting SRB1 bit sends mid-supply voltage to the N inputs
        # use this with a signal generator
        self.hackeeg.wreg(ads1299.MISC1, ads1299.SRB1)

        # Dual-ended mode
        self.hackeeg.wreg(ads1299.MISC1, ads1299.MISC1_const)
        # add channels into bias generation
        # self.hackeeg.wreg(ads1299.BIAS_SENSP, ads1299.BIAS8P)

        if messagepack:
            self.hackeeg.messagepack_mode()
        else:
            self.hackeeg.jsonlines_mode()
        self.hackeeg.start()
        self.hackeeg.rdatac()
        self.launch_read_datastream(self.connector)

        return

    def channel_config_input(self, gain_setting):
        # all channels enabled
        # for channel in range(1, 9):
        #     self.hackeeg.wreg(ads1299.CHnSET + channel, ads1299.TEST_SIGNAL | gain_setting )

        # self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.INT_TEST_DC | gain_setting)
        # self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.INT_TEST_DC | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 2, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 3, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 4, ads1299.ELECTRODE_INPUT | gain_setting)
        self.hackeeg.wreg(ads1299.CHnSET + 5, ads1299.ELECTRODE_INPUT | 0)
        self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.ELECTRODE_INPUT | 0)
        self.hackeeg.wreg(ads1299.CHnSET + 7, ads1299.ELECTRODE_INPUT | 0)
        self.hackeeg.wreg(ads1299.CHnSET + 8, ads1299.ELECTRODE_INPUT | 0)

    def channel_config_test(self):
        # test_signal_mode = ads1299.INT_TEST_DC | ads1299.CONFIG2_const
        test_signal_mode = ads1299.INT_TEST_4HZ | ads1299.CONFIG2_const
        self.hackeeg.wreg(ads1299.CONFIG2, test_signal_mode)
        self.hackeeg.wreg(ads1299.CHnSET + 1, ads1299.INT_TEST_DC | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 2, ads1299.SHORTED | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 3, ads1299.MVDD | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 4, ads1299.BIAS_DRN | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 5, ads1299.BIAS_DRP | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 6, ads1299.TEMP | ads1299.GAIN_1X)
        self.hackeeg.wreg(ads1299.CHnSET + 7, ads1299.TEST_SIGNAL | ads1299.GAIN_1X)
        self.hackeeg.disable_channel(8)

        # all channels enabled
        # for channel in range(1, 9):
        #     self.hackeeg.wreg(ads1299.CHnSET + channel, ads1299.TEST_SIGNAL | gain_setting )
        pass


    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("serial_port", help="serial port device path",
                            type=str)
        parser.add_argument("--debug", "-d", help="enable debugging output",
                            action="store_true")
        parser.add_argument("--samples", "-S", help="how many samples to capture",
                            default=DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE, type=int)
        parser.add_argument("--continuous", "-C", help="read data continuously (until <return> key is pressed)",
                            action="store_true")
        parser.add_argument("--sps", "-s",
                            help=f"ADS1299 samples per second setting- must be one of {sorted(list(SPEEDS.keys()))}, default is {self.samples_per_second}",
                            default=self.samples_per_second, type=int)
        parser.add_argument("--gain", "-g",
                            help=f"ADS1299 gain setting for all channels– must be one of {sorted(list(GAINS.keys()))}, default is {self.gain}",
                            default=self.gain, type=int)
        parser.add_argument("--lsl", "-L",
                            help=f"Send samples to an LSL stream instead of terminal",
                            action="store_true"),
        parser.add_argument("--lsl-stream-name", "-N",
                            help=f"Name of LSL stream to create",
                            default=self.lsl_stream_name, type=str),
        parser.add_argument("--messagepack", "-M",
                            help=f"MessagePack mode– use MessagePack format to send sample data to the host, rather than JSON Lines",
                            action="store_true")
        parser.add_argument("--channel-test", "-T",
                            help=f"set the channels to internal test settings for software testing",
                            action="store_true")
        parser.add_argument("--hex", "-H",
                            help=f"hex mode– output sample data in hexidecimal format for debugging",
                            action="store_true")
        parser.add_argument("--quiet", "-q",
                            help=f"quiet mode– do not print sample data (used for performance testing)",
                            action="store_true")
        parser.add_argument("--fileName", "-f",
                            help=f"data output file name",
                            type=str)
        args = parser.parse_args()
        if args.debug:
            self.debug = True
            print("debug mode on")
        self.samples_per_second = args.sps
        self.gain = args.gain
        self.fileName = args.fileName

        if args.continuous:
            self.continuous_mode = True

        if args.lsl:
            self.lsl = True
            if args.lsl_stream_name:
                self.lsl_stream_name = args.lsl_stream_name
            self.lsl_info = StreamInfo(self.lsl_stream_name, 'EEG', self.channels, self.samples_per_second, 'int32',
                                       self.stream_id)
            self.lsl_outlet = StreamOutlet(self.lsl_info)

        self.serial_port_name = args.serial_port
        self.hackeeg = hackeeg.HackEEGBoard(self.serial_port_name, baudrate=2000000, debug=self.debug)
        # self.non_blocking_console.init(self.hackeeg.raw_serial_port)
        self.non_blocking_console.init()
        self.max_samples = args.samples
        self.channel_test = args.channel_test
        self.quiet = args.quiet
        self.hex = args.hex
        self.messagepack = args.messagepack
        self.hackeeg.connect()
        self.setup(samples_per_second=self.samples_per_second, gain=self.gain, messagepack=self.messagepack)


    def read_datastream(self, queue):
        while self.read_samples_continuously:
            result = self.hackeeg.read_rdatac_response()
            if result:
                status_code = result.get(self.hackeeg.MpStatusCodeKey)
                data = result.get(self.hackeeg.MpDataKey)
                if status_code == Status.Ok and data:
                    timestamp = result.get('timestamp')
                    channel_data = result.get('channel_data')
                    queue.put((timestamp, channel_data))
                else:
                    if not self.quiet:
                        print(data)
            else:
                print("no data to decode")
                print(f"result: {result}")

    def launch_read_datastream(self, queue):
        self.data_process = Process(target=self.read_datastream, args=(queue,))
        self.data_process.start()

    def process_datastream(self, queue):
        while ((len(self.dataMatrix[0])< self.max_samples and not self.continuous_mode) or \
            (self.read_samples_continuously and self.continuous_mode)):
            while not queue.empty():
                timestamp, channel_data = queue.get()
                if not self.quiet:
                    print(f"timestamp:{timestamp} sample_number: {sample_number}| ",
                            end='')
                    for channel_number, sample in enumerate(channel_data):
                        print(f"{channel_number + 1}:{sample}", end='')
                self.dataMatrix[0].append(timestamp)
                for channel_number, sample in enumerate(channel_data):
                    self.dataMatrix[channel_number+1].append(sample)

    def start(self):
        self.pause_toggle = False
        self.read_samples_continuously = True
        processThread = threading.Thread(target=self.process_datastream, args=(self.connector,))
        processThread.start()

        # self.start_time = time.perf_counter()
        print("Started data acquisition thread")

    def remove(self, index):
        for i in range(0,len(self.dataMatrix)):
            del self.dataMatrix[i][0:index]
    
    def stop(self):
        self.data_process.terminate()
        self.data_process.join()
        self.hackeeg.stop_and_sdatac_messagepack()
        self.hackeeg.blink_board_led()

    def main(self):

        #-----Reading in data-----

        self.parse_args()

        self.start()

        while self.read_samples_continuously:
            self.read_keyboard_input()
            continue

        self.stop()


        diffs = np.subtract(self.dataMatrix[0][1:-1],self.dataMatrix[0][0:-2])
        sps = 1000000/(sum(diffs)/len(diffs))
        print("truesps: ", sps)

        


if __name__ == "__main__":
    HackEegTestApplication().main()