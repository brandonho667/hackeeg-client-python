import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style

import tkinter as tk
from tkinter import ttk
from hackeeg_datastream import *

import numpy as np

LARGE_FONT = ("Verdana", 12)
NORMAL_FONT = ("calibre", 10)
style.use("ggplot")

f = Figure(figsize=(5,5), dpi=100)
a = f.add_subplot(111)

dataStream = None
def animate(i):
    global dataStream
    if not dataStream:
        return
    if dataStream.graph_step < dataStream.step:
        np_dataMatrix = np.array(dataStream.dataMatrix[dataStream.graph_step:dataStream.step])
        temp = np_dataMatrix[:,2]
        dataStream.data_stream.extend(temp)
        dataStream.graph_step = dataStream.step
    a.clear()
    a.plot(np.arange(0,len(dataStream.data_stream)), dataStream.data_stream)

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
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="HackEEG GUI Args Selection", font=LARGE_FONT)
        label.grid(column=0)

        # args
        serial_port_var = tk.StringVar()
        samples_var = tk.StringVar()
        sps_var = tk.StringVar()
        gain_var = tk.StringVar()
        filename_var = tk.StringVar()
        continuous_var = tk.IntVar()
        quiet_var = tk.IntVar()
        msgpck_var = tk.IntVar()
        debug_var = tk.IntVar()

        serial_port_label = tk.Label(self, text="Serial Port", font=NORMAL_FONT)
        serial_port_entry = tk.Entry(self, textvariable=serial_port_var, font=NORMAL_FONT)
        serial_port_label.grid(row=1, column=0)
        serial_port_entry.grid(row=1, column=1)

        samples_label = tk.Label(self, text="# of Samples", font=NORMAL_FONT)
        samples_entry = tk.Entry(self, textvariable=samples_var, font=NORMAL_FONT)
        samples_label.grid(row=2, column=0)
        samples_entry.grid(row=2, column=1)

        sps_label = tk.Label(self, text="Samples per Second", font=NORMAL_FONT)
        sps_entry = tk.Entry(self, textvariable=sps_var, font=NORMAL_FONT)
        sps_label.grid(row=3, column=0)
        sps_entry.grid(row=3, column=1)

        gain_label = tk.Label(self, text="Gain", font=NORMAL_FONT)
        gain_entry = tk.Entry(self, textvariable=gain_var, font=NORMAL_FONT)
        gain_label.grid(row=4, column=0)
        gain_entry.grid(row=4, column=1)

        filename_label = tk.Label(self, text="Filename", font=NORMAL_FONT)
        filename_entry = tk.Entry(self, textvariable=filename_var, font=NORMAL_FONT)
        filename_label.grid(row=5, column=0)
        filename_entry.grid(row=5, column=1)

        continuous_check = tk.Checkbutton(self, text="Continuous Mode", variable=continuous_var, onvalue=1, offvalue=0)
        continuous_check.grid(row=6)

        quiet_check = tk.Checkbutton(self, text="Quiet Mode", variable=quiet_var, onvalue=1, offvalue=0)
        quiet_check.grid(row=7)

        msgpck_check = tk.Checkbutton(self, text="MessagePack Mode", variable=msgpck_var, onvalue=1, offvalue=0)
        msgpck_check.grid(row=8)

        debug_check = tk.Checkbutton(self, text="Debug Mode", variable=debug_var, onvalue=1, offvalue=0)
        debug_check.grid(row=9)

        def parse_args():
            args_list = ["serial_port", "samples", "sps", "gain", "filename", "continuous", "quiet", "msgpck", "debug"]
            args = {}
            args["serial_port"] = serial_port_var.get() if serial_port_var.get() != "" else None
            args["samples"] = int(samples_var.get()) if samples_var.get() != "" else 5000
            args["sps"] = int(sps_var.get()) if sps_var.get() != "" else 500
            args["gain"] = int(gain_var.get()) if gain_var.get() != "" else None
            args["filename"] = filename_var.get() if filename_var.get() != "" else None
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
        submit_button.grid(row=10, sticky="nsew")

class RawGraphPage(tk.Frame):
    def __init__(self, parent, controller):
        global dataStream
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="Raw Data Graph", font=LARGE_FONT)
        label.pack(pady=10, padx=10)

        def data_toggle():
            if datathread_button.config('text')[-1] == "Start Data Acquisition":
                dataStream.startDataStream()
                datathread_button.config(text="Stop Data Acquisition")
            else:
                dataStream.stopDataStream()
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

        back_button = ttk.Button(self, text="Back to Args", command=lambda: controller.show_frame(StartPage))
        back_button.pack()

app = HackEEGapp()
anim = animation.FuncAnimation(f, animate, interval=100)
app.mainloop()