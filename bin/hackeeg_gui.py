import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style
from matplotlib import pyplot as plt

import numpy as np

import tkinter as tk
from tkinter import ttk
from hackeeg_datastream import *
import copy

LARGE_FONT = ("Verdana", 12)
NORMAL_FONT = ("calibre", 10)
style.use("ggplot")

f = Figure()
a = f.add_subplot(111)

dataStream = None
graph_step = 0
data = []
for i in range(0,9):
    data.append([])

filename_var = None

def animate(i):
    global dataStream
    global data
    if not dataStream:
        return
    a.clear()
    # get snapshot of dataMatrix
    tmp_ds = copy.deepcopy(dataStream.dataMatrix)
    for i in range(0,len(tmp_ds)):
        data[i].extend(tmp_ds[i])
    sps = 0
    if len(tmp_ds[0]) > 1:
        diffs = np.subtract(tmp_ds[0][1:-1],tmp_ds[0][0:-2])
        sps = 1000000/(sum(diffs)/len(diffs))
    dataStream.remove(len(tmp_ds[0]))
    a.plot(np.arange(0,len(data[1])), data[1])
    a.set_title("Channel 1\nsps: " + str(sps))

def save_window():
    global filename_var
    if not filename_var:
        return
    popup = tk.Tk()
    
    def save_leave():
        with open("../tests/"+filename_var.get(), 'w') as file:
            file.writelines('\t'.join(str(j[i]) for j in data) + '\n' for i in range(0,len(data[0])))
        popup.destroy()

    popup.wm_title("Save Data to File")
    label = ttk.Label(popup, text="File Name", font=NORMAL_FONT)
    label.pack(side="top", padx=10, pady=10)
    filename_entry = tk.Entry(popup, textvariable=filename_var, font=NORMAL_FONT)
    filename_entry.insert(0, filename_var.get())
    filename_entry.pack(padx=10, pady=10)
    save_button = ttk.Button(popup, text="Save", command=save_leave)
    save_button.pack(pady=10)
    popup.mainloop()

def reset():
    global data
    data = []
    for i in range(0,9):
        data.append([])

class HackEEGapp(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        # tk.Tk.iconbitmap(self, default="nameoficon.ico")
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
        menubar.add_cascade(label="Data Stream", menu=datamenu)

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

        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="HackEEG GUI Args Selection", font=LARGE_FONT)
        label.grid(row=0, column=2)
        # self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(3, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(12, weight=1)

        # args
        serial_port_var = tk.StringVar()
        samples_var = tk.StringVar()
        sps_var = tk.StringVar()
        gain_var = tk.StringVar()
        continuous_var = tk.IntVar()
        quiet_var = tk.IntVar()
        msgpck_var = tk.IntVar()
        debug_var = tk.IntVar()
        filename_var = tk.StringVar()

        serial_port_label = tk.Label(self, text="Serial Port", font=NORMAL_FONT)
        serial_port_entry = tk.Entry(self, textvariable=serial_port_var, font=NORMAL_FONT)
        serial_port_label.grid(row=2, column=1, padx=5, pady=5)
        serial_port_entry.grid(row=2, column=2, padx=5, pady=5)

        samples_label = tk.Label(self, text="# of Samples", font=NORMAL_FONT)
        samples_entry = tk.Entry(self, textvariable=samples_var, font=NORMAL_FONT)
        samples_label.grid(row=3, column=1, padx=5, pady=5)
        samples_entry.grid(row=3, column=2, padx=5, pady=5)

        sps_label = tk.Label(self, text="Samples per Second", font=NORMAL_FONT)
        sps_entry = tk.Entry(self, textvariable=sps_var, font=NORMAL_FONT)
        sps_label.grid(row=4, column=1, padx=5, pady=5)
        sps_entry.grid(row=4, column=2, padx=5, pady=5)

        gain_label = tk.Label(self, text="Gain", font=NORMAL_FONT)
        gain_entry = tk.Entry(self, textvariable=gain_var, font=NORMAL_FONT)
        gain_label.grid(row=5, column=1, padx=5, pady=5)
        gain_entry.grid(row=5, column=2, padx=5, pady=5)

        filename_label = tk.Label(self, text="Filename", font=NORMAL_FONT)
        filename_entry = tk.Entry(self, textvariable=filename_var, font=NORMAL_FONT)
        filename_label.grid(row=6, column=1, padx=5, pady=5)
        filename_entry.grid(row=6, column=2, padx=5, pady=5)

        continuous_check = tk.Checkbutton(self, text="Continuous Mode", variable=continuous_var, onvalue=1, offvalue=0)
        continuous_check.grid(row=7, column=2, padx=5, pady=5)

        quiet_check = tk.Checkbutton(self, text="Quiet Mode", variable=quiet_var, onvalue=1, offvalue=0)
        quiet_check.grid(row=8, column=2, padx=5, pady=5)

        msgpck_check = tk.Checkbutton(self, text="MessagePack Mode", variable=msgpck_var, onvalue=1, offvalue=0)
        msgpck_check.grid(row=9, column=2, padx=5, pady=5)

        debug_check = tk.Checkbutton(self, text="Debug Mode", variable=debug_var, onvalue=1, offvalue=0)
        debug_check.grid(row=10, column=2, padx=5, pady=5)

        def parse_args():
            args_list = ["serial_port", "samples", "sps", "gain", "filename", "continuous", "quiet", "msgpck", "debug"]
            args = {}
            args["serial_port"] = serial_port_var.get() if serial_port_var.get() != "" else None
            args["samples"] = int(samples_var.get()) if samples_var.get() != "" else 50000
            args["sps"] = int(sps_var.get()) if sps_var.get() != "" else 500
            args["gain"] = int(gain_var.get()) if gain_var.get() != "" else None
            args["continuous"] = (continuous_var.get() == 1)
            args["quiet"] = (quiet_var.get() == 1)
            args["msgpck"] = (msgpck_var.get() == 1)
            args["debug"] = (debug_var.get() == 1)
            return args

        def submit():
            global dataStream
            dataStream = HackEEGDataStream(parse_args())
            controller.show_frame(RawGraphPage)
            

        submit_button = ttk.Button(self, text="Submit Args", command=submit)
        submit_button.grid(row=11, column=2, sticky="nsew", padx=5, pady=5)

class RawGraphPage(tk.Frame):
    def __init__(self, parent, controller):
        global dataStream
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="Raw Data Graph", font=LARGE_FONT)
        label.pack(pady=10, padx=10)

        def data_toggle():
            if datathread_button.config('text')[-1] == "Start Data Acquisition":
                dataStream.start()
                datathread_button.config(text="Pause Data Acquisition")
            else:
                dataStream.pause()
                datathread_button.config(text="Start Data Acquisition")

        def graph_toggle():
            if graph_button.config('text')[-1] == "Pause Graphing":
                anim.event_source.stop()
                graph_button.config(text="Continue Graphing")
            else:
                anim.event_source.start()
                graph_button.config(text="Pause Graphing")

        datathread_button = ttk.Button(self, text="Start Data Acquisition", command=data_toggle)
        datathread_button.pack()

        graph_button = ttk.Button(self, text="Pause Graphing", command=graph_toggle)
        graph_button.pack()

        canvas = FigureCanvasTkAgg(f, self)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, self)
        toolbar.update()
        canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        def stop_return():
            global dataStream
            global data
            dataStream.stop()
            dataStream = None
            datathread_button.config(text="Start Data Acquisition")
            controller.show_frame(StartPage)
            anim.event_source.start()
            graph_button.config(text="Pause Graphing")
            reset()

        back_button = ttk.Button(self, text="Back to Args", command=stop_return)
        back_button.pack()

app = HackEEGapp()
app.geometry("1280x720")
anim = animation.FuncAnimation(f, animate, interval=1000)
app.mainloop()