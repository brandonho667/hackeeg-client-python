import uuid
import time
import sys
import select
from multiprocessing import Process, Queue, Value
import queue, threading
# import msvcrt

from pylsl import StreamInfo, StreamOutlet

import hackeeg
from hackeeg import ads1299
from hackeeg.driver import SPEEDS, GAINS, Status

DEFAULT_NUMBER_OF_SAMPLES_TO_CAPTURE = 50000


class HackEegTestApplicationException(Exception):
    pass

class HackEEGDataStream:
    """HackEEG commandline tool."""

    def __init__(self, args):
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
        # self.manager = multiprocessing.Manager()
        self.dataMatrix = [] # initialize data matrix to RAM
        for i in range(0,9):
            self.dataMatrix.append([])

        self.debug = args["debug"]
        self.samples_per_second = args["sps"]
        self.gain = args["gain"]
        self.fileName = args["filename"]
        self.continuous_mode = args["continuous"]

        if "lsl" in args:
            self.lsl = True
            if args["lsl_stream_name"]:
                self.lsl_stream_name = args["lsl_stream_name"]
            self.lsl_info = StreamInfo(self.lsl_stream_name, 'EEG', self.channels, self.samples_per_second, 'int32',
                                       self.stream_id)
            self.lsl_outlet = StreamOutlet(self.lsl_info)

        self.serial_port_name = args["serial_port"]
        self.hackeeg = hackeeg.HackEEGBoard(self.serial_port_name, baudrate=2000000, debug=self.debug)
        
        self.max_samples = args["samples"]
        self.quiet = args["quiet"]
        self.messagepack = args["msgpck"]
        
        
        self.hackeeg.connect()
        self.setup(samples_per_second=self.samples_per_second, gain=self.gain, messagepack=self.messagepack)

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
        self.hackeeg.wreg(ads1299.CHnSET + 5, ads1299.ELECTRODE_INPUT | gain_setting)
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
    
    def read_datastream(self, queue):
        while True:
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
                if not self.pause_toggle:
                    with open("../data/"+self.fileName, 'a') as file:
                        file.writelines(str(timestamp) + '\t' + '\t'.join(str(j) for j in channel_data) + '\n')
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

    def pause(self):
        self.read_samples_continuously = False
        self.pause_toggle = True
        
        
    # def save(self):
    #     print('Saving data ....')
    #     if self.fileName:
    #         with open("../tests/"+self.fileName, 'w') as file:
    #             file.writelines('\t'.join(str(j[i]) for j in self.dataMatrix) + '\n' for i in range(0,len(self.dataMatrix[0])))
    #             # save to file

    def remove(self, index):
        for i in range(0,len(self.dataMatrix)):
            del self.dataMatrix[i][0:index]

    def reset(self):
        self.dataMatrix = [] # initialize data matrix to RAM
        for i in range(0,9):
            self.dataMatrix.append([])
        self.start_time = time.perf_counter()
    
    def stop(self):
        self.read_samples_continuously = False
        self.data_process.terminate()
        self.data_process.join()
        self.hackeeg.stop_and_sdatac_messagepack()
        self.hackeeg.blink_board_led()
        

        