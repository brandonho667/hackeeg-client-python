import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style
from matplotlib import pyplot as plt
from datetime import datetime

from scipy import signal

import numpy as np

import tkinter as tk
from tkinter import ttk
from hackeeg_datastream import *
import copy
import threading

LARGE_FONT = ("Verdana", 12)
NORMAL_FONT = ("calibre", 10)
TO_VOLT = 4.5/(2**23)*10**6
style.use("ggplot")

fig = Figure()
subplots = []

# a = fig.add_subplot(111)

dataStream = None
graph_step = 0
data = []
filt_data = []
for i in range(0,9):
    data.append([0]*8)
    filt_data.append([0]*8)

filename_var = None
filt_filename_var = None
filter_var = None
pause_var = False
start_var = False
pause_axes = []
channel_vars = []
num_channel = 0
colors = ['#ff0000','#ffa500','#ffff00','#008000','#0000ff','#4b0082','#ee82ee','k']

sps = 0

c=3
r=2

filt_a,filt_b = [],[]

FILTERS = ['lowpass', 'highpass', 'bandpass', 'bandstop']
filter_args = {}


def animate(i):
    # global a
    global sps
    global dataStream
    # global pause_axes
    # global graph_step

    # if not dataStream:
    #     return

    # graph_ds = data[0][graph_step:]
    
    # a.clear()
    
    # update_graph()
    # if sps != 0:
    #     a.set_title("Channel Data\nsps: " + str(int(sps)))
    # a.autoscale(axis='x', tight=True)
    # if pause_var:
    #     a.axis(pause_axes)
    #     anim.event_source.stop()

    global fig, subplots, start_var

    # plt.close(fig)

    if not dataStream:
        return

    if sps != 0:
        fig.suptitle("Channel Data\nsps: " + str(int(sps)))

    chnls = []
    for j, c in enumerate(channel_vars):
        if c.get():
            chnls.append(j)
    # print(chnls)

    if start_var:
        fig.clear()
        subplots = [0]*len(chnls)

        for i, ch in enumerate(chnls):
            subplots[i] = fig.add_subplot(len(chnls),1,i+1)
        start_var = False    

    # reorg
    elif len(subplots) != len(chnls):
        fig.clear()
        subplots = [0]*len(chnls)
    
        for i, ch in enumerate(chnls):
            subplots[i] = fig.add_subplot(len(chnls),1,i+1)

    f_n = 9 if pause_var or len(filt_data[1]) <= 40000 else len(filt_data[1])-40000
    f_end = len(filt_data[1])
    n = 9 if pause_var or len(data[1]) <= 40000 else len(data[1])-40000
    end = len(data[1])
    
    for i, ch in enumerate(chnls):
        subplots[i].clear()
        subplots[i].autoscale(axis='x', tight=True)

        if filter_var.get():
            graph_data = filt_data[i+1][f_n:f_end]
            subplots[i].plot(np.arange(f_n,f_n+len(graph_data)), graph_data, colors[ch], label="Ch."+str(ch+1))
        else:
            graph_data = data[i+1][n:end]
            subplots[i].plot(np.arange(n, n+len(graph_data)), graph_data, colors[ch], label="Ch."+str(ch+1))
        subplots[i].legend(loc=1)
        if pause_var:
            subplots[i].axis(pause_axes)

    if pause_var:
        for i in range(len(subplots)-1):
            subplots[i].sharex(subplots[i-1])
            subplots[i].sharey(subplots[i-1])
        anim.event_source.stop()


# def update_graph():
#     global data
#     global pause_var
#     global channel_vars
    
#     # select data from filters
#     for i in range(0,8):
#         if channel_vars[i].get():
#             f_n = 9 if pause_var or len(filt_data[1]) <= 40000 else len(filt_data[1])-40000
#             n = 9 if pause_var or len(data[1]) <= 40000 else len(data[1])-40000
#             if filter_var.get():
#                 graph_data = copy.deepcopy(filt_data[i+1][f_n:])
#                 a.plot(np.arange(f_n,f_n+len(graph_data)), graph_data, colors[i], label="Ch."+str(i+1))
#             else:
#                 graph_data = copy.deepcopy(data[i+1][n:])
#                 a.plot(np.arange(n, n+len(graph_data)), graph_data, colors[i], label="Ch."+str(i+1))
    # a.legend(loc=1)
    
def save_window():
    global filt_filename_var
    popup = tk.Tk()
    
    
    def save_leave():
        global data
        global filt_filename_var
        with open("../data/"+filt_filename_var.get(), 'w') as file:
            file.writelines('\t'.join(str(j[i]) for j in data) + '\n' for i in range(9,len(data[0])))
        popup.destroy()

    popup.wm_title("Save Filtered Data to File")
    label = ttk.Label(popup, text="File Name", font=NORMAL_FONT)
    label.pack(side="top", padx=10, pady=10)
    filt_filename_var = tk.StringVar(popup, value="Filt_Data - "+datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))
    filename_entry = tk.Entry(popup, textvariable=filt_filename_var, font=NORMAL_FONT)
    # filename_entry.insert(0, filt_filename_var.get())
    filename_entry.pack(padx=10, pady=10)
    save_button = ttk.Button(popup, text="Save", command=save_leave)
    save_button.pack(pady=10)
    popup.mainloop()

def reset():
    global data
    global filt_data
    data = []
    filt_data=[]
    for i in range(0,9):
        data.append([0]*8)
        filt_data.append([0]*8)

class HackEEGapp(tk.Tk):
    def __init__(self, *args, **kwargs):
        global filter_var
        global channel_vars

        tk.Tk.__init__(self, *args, **kwargs)

        # tk.Tk.iconbitmap(self, "/home/LermanLab/hackeeg-client-python/bin/troy.ico")
        tk.Tk.wm_title(self, "HackEEG GUI")

        container = tk.Frame(self) # init window

        # defines organization of widgets in window
        container.pack(side="top", fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        menubar = tk.Menu(container)
        datamenu = tk.Menu(menubar, tearoff=0)
        datamenu.add_command(label="Save", command=save_window)
        datamenu.add_command(label="Reset", command=reset)

        # datamenu.add_separator()
        # filemenu.add_command(label="Exit")
        menubar.add_cascade(label="Data", menu=datamenu)

        # lowpass_var = tk.IntVar()
        filtermenu = tk.Menu(menubar, tearoff=0)
        filter_var = tk.IntVar(value=0)
        filtermenu.add_checkbutton(label="Toggle Filter", onvalue=1, offvalue=0, variable=filter_var)

        menubar.add_cascade(label="Filter", menu=filtermenu)
        
        channelmenu = tk.Menu(menubar, tearoff=0)
        for i in range(0,8):
            channel_vars.append(tk.IntVar(value=0))
            channelmenu.add_checkbutton(label="Channel " + str(i+1), onvalue=1, offvalue=0, variable=channel_vars[i])
        menubar.add_cascade(label="View", menu=channelmenu)

        tk.Tk.config(self, menu=menubar)

        self.frames = {} # dict of different windows

        for Page in (StartPage, RawGraphPage):
            frame = Page(container, self) # init frames with StartPage
            self.frames[Page] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(StartPage)
    
    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
    

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        global filename_var
        global c,r
        global filter_args

        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="HackEEG GUI Args Selection", font=LARGE_FONT)
        label.grid(row=0, column=c, sticky="nesw")
        # self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(6, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(r+10, weight=1)


        # args
        serial_port_var = tk.StringVar(value="/dev/ttyACM0")
        samples_var = tk.IntVar()
        sps_var = tk.IntVar(value=8000)
        gain_var = tk.IntVar(value=24)
        continuous_var = tk.IntVar(value=1)
        quiet_var = tk.IntVar(value=1)
        msgpck_var = tk.IntVar()
        debug_var = tk.IntVar()
        filename_var = tk.StringVar(value="RAW_DATA - "+datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))

        # signal args
        signal_label = tk.Label(self, text="Signal", font=NORMAL_FONT)
        signal_label.grid(row=r, column=c-1, padx=10, pady=10)

        serial_port_label = tk.Label(self, text="Serial Port", font=NORMAL_FONT)
        serial_port_entry = tk.Entry(self, textvariable=serial_port_var, font=NORMAL_FONT)
        serial_port_label.grid(row=r+1, column=c-2, padx=5, pady=5)
        serial_port_entry.grid(row=r+1, column=c-1, padx=5, pady=5)

        # samples_label = tk.Label(self, text="# of Samples", font=NORMAL_FONT)
        # samples_entry = tk.Entry(self, textvariable=samples_var, font=NORMAL_FONT)
        # samples_label.grid(row=r+2, column=c-2, padx=5, pady=5)
        # samples_entry.grid(row=r+2, column=c-1, padx=5, pady=5)

        sps_label = tk.Label(self, text="Samples per Second", font=NORMAL_FONT)
        sps_entry = tk.Entry(self, textvariable=sps_var, font=NORMAL_FONT)
        sps_label.grid(row=r+2, column=c-2, padx=5, pady=5)
        sps_entry.grid(row=r+2, column=c-1, padx=5, pady=5)

        gain_label = tk.Label(self, text="Gain", font=NORMAL_FONT)
        gain_entry = tk.Entry(self, textvariable=gain_var, font=NORMAL_FONT)
        gain_label.grid(row=r+3, column=c-2, padx=5, pady=5)
        gain_entry.grid(row=r+3, column=c-1, padx=5, pady=5)

        filename_label = tk.Label(self, text="Filename", font=NORMAL_FONT)
        filename_entry = tk.Entry(self, textvariable=filename_var, font=NORMAL_FONT)
        filename_label.grid(row=r+4, column=c-2, padx=5, pady=5)
        filename_entry.grid(row=r+4, column=c-1, padx=5, pady=5)

        # mode args
        mode_label = tk.Label(self, text="Modes", font=NORMAL_FONT)
        mode_label.grid(row=r, column=c, padx=10, pady=10)

        continuous_check = tk.Checkbutton(self, text="Continuous Mode", variable=continuous_var, onvalue=1, offvalue=0)
        continuous_check.grid(row=r+1, column=c, padx=5, pady=5)

        quiet_check = tk.Checkbutton(self, text="Quiet Mode", variable=quiet_var, onvalue=1, offvalue=0)
        quiet_check.grid(row=r+2, column=c, padx=5, pady=5)

        msgpck_check = tk.Checkbutton(self, text="MessagePack Mode", variable=msgpck_var, onvalue=1, offvalue=0)
        msgpck_check.grid(row=r+3, column=c, padx=5, pady=5)

        debug_check = tk.Checkbutton(self, text="Debug Mode", variable=debug_var, onvalue=1, offvalue=0)
        debug_check.grid(row=r+4, column=c, padx=5, pady=5)

        # filter args
        filter_args["N"] = tk.IntVar(value=4) # order of filter
        filter_args["rp"] = tk.StringVar(value="0.1") # max ripple allowed below unity gain in passband (dB)
        filter_args["rs"] = tk.StringVar(value="40") # minimum attenuation required in the stop band (dB)
        filter_args["Wn"] = tk.StringVar(value="50, 900") # crit fqs
        filter_args["btype"] = tk.StringVar(value=FILTERS[2]) # filter selection
        filter_label = tk.Label(self, text="Filter", font=NORMAL_FONT)
        filter_option = tk.OptionMenu(self, filter_args["btype"], *FILTERS)
        filter_label.grid(row=r, column=c+1, padx=5, pady=5)
        filter_option.grid(row=r, column=c+2, padx=5, pady=5)

        N_label = tk.Label(self, text="Order", font=NORMAL_FONT)
        N_entry = tk.Entry(self, textvariable=filter_args["N"])
        N_label.grid(row=r+1, column=c+1, padx=5, pady=5)
        N_entry.grid(row=r+1, column=c+2, padx=5, pady=5)
        
        rp_label = tk.Label(self, text="Ripple (dB)", font=NORMAL_FONT)
        rp_entry = tk.Entry(self, textvariable=filter_args["rp"])
        rp_label.grid(row=r+2, column=c+1, padx=5, pady=5)
        rp_entry.grid(row=r+2, column=c+2, padx=5, pady=5)

        rs_label = tk.Label(self, text="Attenuation (dB)", font=NORMAL_FONT)
        rs_entry = tk.Entry(self, textvariable=filter_args["rs"])
        rs_label.grid(row=r+3, column=c+1, padx=5, pady=5)
        rs_entry.grid(row=r+3, column=c+2, padx=5, pady=5)

        Wn_label = tk.Label(self, text="Crit Fqs", font=NORMAL_FONT)
        Wn_entry = tk.Entry(self, textvariable=filter_args["Wn"])
        Wn_label.grid(row=r+4, column=c+1, padx=5, pady=5)
        Wn_entry.grid(row=r+4, column=c+2, padx=5, pady=5)

        def parse_args():
            # args_list = ["serial_port", "samples", "sps", "gain", "filename", "continuous", "quiet", "msgpck", "debug"]
            args = {}
            args["filename"] = filename_var.get() if filename_var.get() != "" else "RAW_DATA - "+datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
            args["serial_port"] = serial_port_var.get() if serial_port_var.get() != "" else None
            args["samples"] = samples_var.get() if samples_var.get() != 0 else 50000
            args["sps"] = sps_var.get() if sps_var.get() != 0 else 500
            args["gain"] = gain_var.get() if gain_var.get() != 0 else None
            args["continuous"] = (continuous_var.get() == 1)
            args["quiet"] = (quiet_var.get() == 1)
            args["msgpck"] = (msgpck_var.get() == 1)
            args["debug"] = (debug_var.get() == 1)
            return args

        def submit():
            global dataStream
            global filt_a,filt_b
            global filter_args
            dataStream = HackEEGDataStream(parse_args())
            filter_vals = {}
            filter_vals["N"] = filter_args["N"].get()
            filter_vals["rp"] = float(filter_args["rp"].get())
            filter_vals["rs"] = float(filter_args["rs"].get())
            filter_vals["Wn"] = [int(x)*2/sps_var.get() for x in filter_args["Wn"].get().split(", ")]
            filter_vals["btype"] = filter_args["btype"].get()
            filter_vals["analog"] = False
            print(filter_vals)
            filt_b,filt_a = signal.ellip(**filter_vals)
            print(filt_b,filt_a)
            controller.show_frame(RawGraphPage)
            

        submit_button = ttk.Button(self, text="Submit Args", command=submit)
        submit_button.grid(row=r+9, column=c, sticky="nsew", padx=5, pady=5)

class RawGraphPage(tk.Frame):
    def __init__(self, parent, controller):
        global dataStream
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="Raw Data Graph", font=LARGE_FONT)
        label.pack(pady=10, padx=10)

        def data_toggle():
            if datathread_button.config('text')[-1] == "Start Data Acquisition":
                global subplots
                dataStream.start()
                filter_data()
                datathread_button.config(text="Pause Data Acquisition")
            else:
                dataStream.pause()
                datathread_button.config(text="Start Data Acquisition")

        def graph_toggle():
            global pause_var
            global start_var
            global pause_axes
            if graph_button.config('text')[-1] == "Pause Graphing":
                pause_var = True
                if subplots[0]:
                    xmin, xmax, ymin, ymax = subplots[0].axis()
                    pause_axes = [xmin, xmax, ymin, ymax]
                graph_button.config(text="Continue Graphing")
            else:
                pause_var = False
                start_var = True
                anim.event_source.start()
                graph_button.config(text="Pause Graphing")

        datathread_button = ttk.Button(self, text="Start Data Acquisition", command=data_toggle)
        datathread_button.pack()

        graph_button = ttk.Button(self, text="Pause Graphing", command=graph_toggle)
        graph_button.pack()

        canvas = FigureCanvasTkAgg(fig, self)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, self)
        toolbar.update()
        canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        def filter_data():
            global dataStream
            global data
            global sps
            
            def filter(ch, len_new):
                global data
                global filt_data 
                global filter_args
                global filt_a
                global filt_b

                # filt_data[ch].extend(signal.lfilter(filt_b, filt_a, data[ch][-len_new:]))

                for k in range(len(data[ch])-len_new, len(data[ch])):
                    y_k = filt_b[0]*data[ch][k]
                    for n in range(1, len(filt_a)):
                        y_k += filt_b[n]*data[ch][k-n]-filt_a[n]*filt_data[ch][k-n]
                    filt_data[ch].append(y_k)

            # print("HA")
            if not dataStream or dataStream.pause_toggle:
                return
            
            tmp_ds = dataStream.dataMatrix[0:len(dataStream.dataMatrix)]

            sps = 0
            if len(tmp_ds[0]) > 9:
                diffs = np.subtract(tmp_ds[0][1:-1],tmp_ds[0][0:-2])
                sps = 1000000/(sum(diffs)/len(diffs))

            for i in range(0,len(tmp_ds)):
                if i != 0:
                    tmp_ds[i] = [d*TO_VOLT for d in tmp_ds[i]]
                data[i].extend(tmp_ds[i])
                if len(data[i]) <= 9 or i == 0:
                    continue
                data[i][-9-len(tmp_ds[i]):] = signal.medfilt(data[i][-9-len(tmp_ds[i]):], kernel_size=9)
                filter(i, len(tmp_ds[i]))
            dataStream.remove(len(tmp_ds[0]))
            threading.Timer(0.5, filter_data).start()

        def stop_return():
            global dataStream
            global filename_var
            dataStream.stop()
            dataStream = None
            filename_var = tk.StringVar(value="RAW_DATA - "+datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))
            datathread_button.config(text="Start Data Acquisition")
            controller.show_frame(StartPage)
            anim.event_source.start()
            graph_button.config(text="Pause Graphing")
            reset()

        back_button = ttk.Button(self, text="Back to Args", command=stop_return)
        back_button.pack()

app = HackEEGapp()
app.geometry("1280x720")
anim = animation.FuncAnimation(fig, animate, interval=500)

app.mainloop()