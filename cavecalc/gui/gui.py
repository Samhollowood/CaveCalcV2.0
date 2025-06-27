"""Codes for the Cavecalc GUIs.

The GUIs provide a simple user-friendly interface for Cavecalc. They do not
expose the full model functionality but allow most common calculations to be
performed.

GUIs may be accessed by running the scripts:
    cc_input_gui.py
    cc_output_gui.py
"""

import os

import copy
import importlib.resources
import subprocess
from collections import OrderedDict
import operator
from numpy import linspace
import matplotlib
from sys import platform
if platform != 'win32':
    matplotlib.use('TkAgg') # necessary for mac
from matplotlib import pyplot as plt
from tkinter import *
from tkinter import filedialog
from cavecalc.analyse import Evaluate
import cavecalc.data.types_and_limits
import cavecalc.gui
import cavecalc.gui.mapping  
import cavecalc.gui.layout
from cavecalc.setter import SettingsMaker, NameSwitcher, SettingsObject
import time
from tkinter import Toplevel, Label  # Ensure Toplevel is imported
from tkinter import messagebox
from tkinter import ttk

# settings options hidden from plotting menus (useless clutter)
HIDE_OPS = True
HIDDEN_OPTS = [
    'totals',  'molalities',   'isotopes',     'out_dir', 
    'phreeqc_log_file',        'phreeqc_log_file_name',
    'database'] # options not available for plotting

ns = NameSwitcher()


def od(dict):
    """Converts a dict to an ordered dict, sorted by key."""
    
    return OrderedDict(sorted(dict.items()))

def py2tk(dict):
    """Converts a dict to Tkinter types.
    
    Convert dictionary entries from doubles and strings to StringVar for use 
    with tkinter. Returns a modified copy.
    
    Args:
        dict: A dict with entries that are simple data types.
    Returns:
        A modified dict.
    """
    
    out = copy.copy(dict)
    types = vars(cavecalc.data.types_and_limits).copy()
    
    for k in dict.keys():
        if type(types[k]) is bool:
            out[k] = BooleanVar()
            out[k].set(False)
        elif dict[k] is not None:
            out[k] = StringVar()
            out[k].set(dict[k])
        else:
            out[k] = None
    return out
    
def _parse_value_input(string, allow=[]):
    """
    Parses leftmost panel input to detect ranges of values or single values.
    Returns either a double or a list of doubles.
    """
    a = string
    
    # remove brackets
    rm = ['(', ')', '[', ']']
    for s in rm:
        if s not in allow:
            a = a.replace(s,'')
    
    # replace commas with space
    a = a.replace(',',' ')
    
    #split string on spaces
    a = a.split(' ')
    
    # attempt conversion to float (most data types are numeric)
    try:
        b = [float(v) for v in a if v != '']
    except ValueError:
        b = [str(v) for v in a if v!= '']
    
    # remove list structure from single entries
    if len(b) == 1:
        b = b[0]
    
    return b
    
def tk2py(dict, parse=False):
    """Inverse of py2tk.
    
    Convert a dict of tkinter StringVar types to a a dict understandable by
    the cavecalc setter module.
    
    Args:
        dict: A dict full of GUI inputs (e.g. StringVar types)
        parse (optional): If True, process numeric input to get a list of
            values if possible. Default False.
    Returns:
        A dictionary of booleans, strings, lists and floats.
    """    
    
    a = dict.copy()
    for k in dict.keys():
        if dict[k] is None:
            a[k] = None
        elif type(dict[k].get()) is str:
            if parse:
                a[k] = _parse_value_input(dict[k].get())
            else:
                a[k] = dict[k].get()
        else:
            a[k] = dict[k].get()
        
    b = {k:v for k,v in a.items() if v is not None}
    return b

def gplot(  x_values, y_values, x_label, y_label, 
           label_vals, label_name ):
    """Plot data in a new window.
    
    This plotting function is a simplified version of the plotting code used in
    the analyse module for use with the GUI. If x_values contains lists of
    length 1, a single series is plotted, connecting data points from all
    models together. If length > 1 then each model is plotted as a separate 
    series.
    
    If more advanced plotting is required... use something else.
    
    Args:
        x_values: A list of lists containing the model output to be plotted on
            the x-axis.
        y_values: A list of lists containing the model output to be plotted on
            the y-axis.
        x_label (str): x-axis label.
        y_label (Str): y-axis label.
        label_vals = A list of values to label the series with.
        label_name (str) = The name of the data in label_vals.
    
    """

    fig, ax = plt.subplots()
    
    # if plotting... a single point from each model
    if all(len(x) == 1 for x in x_values):
        xs = [x[0] for x in x_values]
        ys = [y[0] for y in y_values]
        
        ax.plot(xs, ys, 'x--')
        
        if label_name:
            for label, x, y in zip(label_vals, xs, ys):
                ax.annotate(    "%s=%s" % (label_name, label), 
                                xy = (x,y), fontsize=8)
        plt.ylabel(y_label)
        plt.xlabel(x_label)
        
        plt.show(block=False)
     
    # else plot each model as it's own series
    else:
        for (i, xs) in enumerate(x_values):
            ys = y_values[i]
            if label_name:
                l_str = "%s: %s" % (label_name, label_vals[i])
                ax.plot(xs, ys, label = l_str)
                ax.legend(prop={'size':8})
            else:
                ax.plot(xs, ys)
            
        plt.ylabel(y_label)
        plt.xlabel(x_label)
        
        plt.show(block=False)
        
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None

        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip:
            return
        
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = Label(self.tooltip, text=self.text, background="lightyellow", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None        
    
class FileFindWidget(Frame):
    """A Tkinter Widget for opening a file browser window."""
    
    def __init__(self, master=None, value=None, mode=None):
        super().__init__(master)
        self.master = master
        self.value = value
        
        self.entry = Entry(self, textvariable=value).grid(row=0, column=0)
        
        if mode.capitalize() == 'Load':
            self.button = Button(self, text='browse', command= self._openfilename)
        elif mode.capitalize() == 'Save':
            self.button = Button(self, text='browse', command= self._saveasfilename)
        elif mode.capitalize() == 'Dir':
            self.button = Button(self, text='browse', command= self._getdirectory)
        else:
            raise ValueError("Mode %s not recognised. Use save or load." % mode)
        self.button.grid(row=0, column=1)
        
    def _openfilename(self, event=None):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.value.set(file_path)
        
    def _saveasfilename(self, event=None):
        file_path = filedialog.asksaveasfilename()
        if file_path:
            self.value.set(file_path)
            
    def _getdirectory(self, event=None):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.value.set(dir_path)
             
class InputsRangeWidget(Frame):
    """A compound widget for inputting a range of numeric values.

    The InputsRangeWidget contains an Entry field for inputting a single (or
    multiple values) manually. It also has a 'Set Range' button that opens
    a new window for generating an equally-spaced sequence.
    """
    
    def __init__(self, master=None, value=None):
        super().__init__(master)
        self.master = master
        self.value = value
        self.min = DoubleVar()
        self.max = DoubleVar()
        self.steps = DoubleVar()
        
        self.entry = Entry(self, textvariable=self.value)
        self.entry.grid(row=0, column=0)
        self.button = Button(self, text='*', command=self.select_range)
        self.button.grid(row=0, column=1)
    
    def select_range(self):
        """Creates new window to input range information."""
        
        def get_range(): 
            try: 
                # Get and convert inputs
                min_val = float(self.min.get())
                max_val = float(self.max.get())
                steps = int(float(self.steps.get()))  # Convert to integer 
                
                # Generate the range using linspace
                vals = linspace(min_val, max_val, num=steps)
                self.value.set(vals.tolist())
                top.destroy() 
            except ValueError as e: 
                print(f"Error: {e}. Ensure all inputs are numbers.") 
            except TypeError as e: 
                print(f"Error: {e}. Ensure 'steps' is an integer.")

        top = Toplevel(self)
        top.title("Select Range")  # Set the window title
        Label(top, text="Select Range").grid(row=0, columnspan=2)
        Label(top, text="Min").grid(row=1)
        Label(top, text="Max").grid(row=2)
        Label(top, text="Steps").grid(row=3)
    
        # Create entry fields for min, max, and steps
        e1 = Entry(top, textvariable=self.min).grid(row=1, column=1)
        e2 = Entry(top, textvariable=self.max).grid(row=2, column=1)
        e3 = Entry(top, textvariable=self.steps).grid(row=3, column=1)
    
        # Add OK and Cancel buttons
        Button(top, text="OK", command=get_range).grid(row=4)
        Button(top, text="Cancel", command=top.destroy).grid(row=4, column=1)

class OptsWidget(Frame):
    def __init__(self, master, parameter, value, options, row):
        super().__init__(master)
        self.r = row
        self.master = master
        self.parameter = parameter
        self.value = value
        self.options = options
        
        assert type(options) is list
            
        self.l = Label(master, text=self.parameter)
        self.l.grid(row=self.r, column=0, sticky=W)
        self.o = OptionMenu(master, self.value, *self.options)
        self.o.grid(row=self.r, column=1)
        
class InputsWidget(Frame):
    def __init__(self, master, parameter, value, row):
        super().__init__(master)
        self.r = row
        self.master = master
        self.parameter = parameter
        self.value = value
        
        self.l = Label(master, text=parameter)
        self.l.grid(row=self.r, column=0, sticky=W)
        self.o = Entry(master, textvariable=value)
        self.o.grid(row=self.r, column=1)
             
class CCInputGUI(object):
    """The Cavecalc input GUI window."""
    
    def __init__(self, master):
        """Initialise - Open the window."""
        """Initialize the main GUI."""
        
        self.master = master
        
        self.master.title('Cavecalc Model Input GUI')
              
        # Show loading screen
        self._show_loading_screen()
        self._load_defaults()
        self.CDA_input_path = StringVar()
        self.CDA_path = StringVar()
        self.construct_inputs()
       
        
    def _show_loading_screen(self):
        """Display a loading screen with a welcome message and call the initialization callback."""
        
        # Create a loading screen
        loading_screen = Toplevel(self.master)
        loading_screen.title("Welcome!")
        
        # Set the dimensions and position of the loading screen
        loading_screen.geometry("300x150")
        
        # Create a label with the welcome message
        label = Label(loading_screen, text="Welcome to CaveCalc v2.0", font=("Arial", 16))
        label.pack(expand=True)
        
        # Create another label for the additional message
        additional_label = Label(loading_screen, text="Always go feet first into CaveCalc", font=("Arial", 12,))
        additional_label.pack(expand=True)
        
        # Function to close the loading screen and call the callback
        def close_loading_screen():
            loading_screen.destroy()
        
        # Schedule the loading screen to close after 3 seconds
        loading_screen.after(10000, close_loading_screen)    
        
    def _loop_gen(self, layout_numbers): 
        ln = layout_numbers
        if type(ln) is int: 
            ln = [ln] 
        elif type(ln) is not list: 
            raise TypeError("layout_numbers must be int or list of ints.")
    
        # Desired order of variables
        desired_order = [
        'user_filepath',
        'tolerance_d13C',
        'tolerance_d18O',
        'tolerance_DCP',
        'tolerance_d44Ca',
        'tolerance_MgCa',
        'tolerance_SrCa',
        'tolerance_BaCa',
        'tolerance_UCa',
        'out_dir' 
        ]
    
        # Generate the list of settings based on layout numbers
        g = [(k, self.layout[k][1]) for k in self.settings.keys() if self.layout[k][0] in ln]
        
        # Sort based on the desired order 
        return sorted(g, key=lambda tup: desired_order.index(tup[0]) if tup[0] in desired_order else float('inf'))
         
        
    def get_ln(self, key):
        """Gets the layout index number of 'key'"""
        
        try:
            return self.layout[key][1]
        except KeyError:
            return self.layout[ns(key)][1]
        
    def _load_defaults(self):
    
        self.d = SettingsObject()

        self.units = vars(cavecalc.data.types_and_limits).copy()
        self.layout = vars(cavecalc.gui.layout).copy()
        
        settings = self.d.dict()
        self.settings = py2tk(settings)
        
    def _browse_file(self, path_variable):  
       """Opens a file dialog to select a file and sets the given StringVar.""" 
       filename = filedialog.askopenfilename()  
       if filename: 
           path_variable.set(filename)      
      
    def _plot_CDA(self): 
        """Opens the plotting window with the user-provided file paths."""
        s = self.settings.copy()
        dir1 = s.pop('user_filepath').get()
        dir2 = self.CDA_path.get()

        if not dir1 or not dir2:
            print("Both file paths are required!")
            return

        try: 
            evaluator = Evaluate()
            print("Plotting...")
            evaluator.plot_CDA(dir1, dir2)
            plt.show(block=False)
            plt.pause(1)
        except Exception as e:  
            print(f"Error while plotting: {e}") 
            
    def _show_help(self): 
        """Opens the CDA_help.txt file in the default text viewer.""" 
        try: 
            # Locate the help file within the cavecalc.gui package using importlib.resources 
            with importlib.resources.path(cavecalc.gui, 'CDA_help.txt') as help_file_path: 
                help_file_path_str = str(help_file_path)  # Convert PosixPath to string
            
                # Open the file with the default application
                if subprocess.os.name == 'nt':  # For Windows 
                   subprocess.run(['start', help_file_path_str], shell=True) 
                elif subprocess.os.name == 'posix':  # For macOS and Linux 
                     if 'darwin' in subprocess.os.uname().sysname.lower():  # For macOS 
                         subprocess.run(['open', help_file_path_str])
                     else:  # For Linux 
                         subprocess.run(['xdg-open', help_file_path_str])
                else: 
                    print("Unsupported operating system for opening help files.")
        except Exception as e: 
            print(f"Error while opening help file: {e}")       
              
        
    def construct_inputs(self):
        """Frame 1 contains the left-hand panel of the input GUI."""

        def add_things_to_frame(frame, layout_number, header_text, i, highlight=False, font=None):
            if highlight: 
                # Create a frame to highlight the section with a dark green border
                highlight_frame = Frame(frame, bd=2, relief='solid', highlightbackground='green', highlightcolor='green', padx=10, pady=10)
                highlight_frame.grid(row=i, column=0, columnspan=3, sticky='nsew', pady=5)
                frame = highlight_frame  # Use the highlighted frame as the current frame
            
            # Create a dictionary for variable tooltips 
            tooltips_variables = {
                #CDA
                'soil_d13C': 'Sets the stbale carbon isotopic composition of the soil-water and soil-gas. Impacts speleothem d13C', 
                'soil_pCO2': 'Sets the concentrations of CO2 witin the soil. Alters the extent of bedrock dissolution, and amount of degassing steps. Impacts d13C, d44Ca, DCP, and X/Ca', 
                'cave_pCO2': 'Sets the concentration of cave air CO2. Alters the amount of degassing and prior carbonate precipitation. Impacts d13C, d44Ca and X/Ca', 
                'gas_volume': 'Sets the conditions of bedrock dissolution. More open-system conditions is given by a higher gas volume. Impacts DCP and d13C', 
                'temperature': 'Alters temperature of the cave environment. Impacts fractionation factors of d18O, d13C, and partitioninng coefficients of X/Ca ', 
                'atm_d18O': 'Sets the rainfall (‰, SMOW) value infilitrating into the karst. Impacts d18O',
                
                #Other
                'atm_O2': 'Sets the atmospheric O2 (given as a decimal fraction)',
                'atm_pCO2': 'Provides the concentration of atmospheric pCO2. If atmo_exchange > 0, will impact soil-water equilibriation',
                'atm_d13C': 'Provides the stable carbon isotope composition of atmospheric pCO2. If atmo_exchange > 0, will impact d13C after soil-water equilibriation',
                'atm_R14C': 'Sets the radiocarbon activity of atmospheric 14C',
                'soil_O2': 'Sets the percentage of O2 gas within the soil (given as a decimal fraction). If bedrock_pyrite > 0, will impact the amount of pyrite oxidation',
                'soil_R14C': 'Sets the radiocarbon activity within the soil. Impacts DCP',
                # Soil Gas Mixing
                'atmo_exchange': 'Sets the amount of atmospheric excahnge with the soil, impacting soil-water equilibriation',
                'init_O2':     'A mix of the soil and atm O2. Defines the final soilwater gas O2',  
                'init_R14C':	'A mix of the soil and atm R14C. Defines final soilwater gas R14C',  	
                'init_d13C':	'A mix of the soil and atm d13C. Defines final soilwater gas d13C',  	
                'init_pCO2':	'A mix of the soil and atm pCO2. Defines final soilwater gas pCO2',  	
                
                'soil_Ba': 'Alters the amount of Ba provided by the soil. Impacts Ba/Ca',
                'soil_Ca':  'Alters the amount of Ca provided by the soil. Impacts X/Ca',
                'soil_Mg':  'Alters the amount of Ca provided by the soil. Impacts Mg/Ca',
                'soil_Sr': 'Alters the amount of Ca provided by the soil. Impacts Sr/Ca',
                'soil_U':  'Alters the amount of Ca provided by the soil. Impacts U/Ca',
                'soil_d44Ca':  'Alters the d44Ca of the soil. Impacts d44Ca',
                
                'bedrock_BaCa': 'Alters the amount of Ba provided by the bedrock. Impacts Ba/Ca',
                'bedrock_Ca':  'Alters the amount of Ca provided by the bedrock. Impacts X/Ca',
                'bedrock_MgCa':  'Alters the amount of Mg provided by the bedrock. Impacts Mg/Ca',
                'bedrock_SrCa': 'Alters the amount of Sr provided by the bedrock. Impacts Sr/Ca',
                'bedrock_UCa':  'Alters the amount of U provided by the bedrock. Impacts U/Ca',
                'bedrock_d44Ca':  'Alters the d44Ca of the bedrock. Impacts d44Ca',
                'bedrock_d13C':  'Alters the d13C of the bedrock. Impacts d13C',
                'bedrock_d18O':  'Alters the d18O of the bedrock. Impacts d18O',
                
                
            
                # Bedrock Dissolution Conditions
                'bedrock': 'Alters the amount if bedrock equilibriation with the soil gas. Impacts d13C and DCP',
                'bedrock_pyrite': 'Alters the amount of pryite available for oxidation. Amount of oxidation also a function of soil_O2. Impacts d13C and DCP',                
                'reprecip': 'Controls whether re-precipitation can occur. Impacts d13C, d44Ca and X/Ca',
                
                # Cave Air   
                'cave_d13C': 'Alters the stable carbon isotope composition of cave air. NOTE: Default mode does not allow for equilibriaiton with the cave air. To do so, change Degassing/Precipitation Mode to single_step_degassing',
                'cave_R14C':  'Alters the radiocarbon value of cave air that is equilibriated with the solution R14C. NOTE: Default CaveCalc mode does not allow for equilibriaiton with the cave air. Change Degassing/Precipitation Mode to single_step_degassing to test',
                'cave_d18O':  'Alters the cave air d18O that is equilibriated with the solution d18O. NOTE: Default CaveCalc mode does not allow for equilibriaiton with the cave air. Change Degassing/Precipitation Mode to single_step_degassing to test',
                'cave_air_volume': 'Alters the extent of equilibriation with the cave air. NOTE: Default CaveCalc mode does not allow for equilibriaiton with the cave air. Change Degassing/Precipitation Mode to single_step_degassing to test',

                'kinetics_mode': 'Alters fundamental aspects of speleothem chemistry. Refer to Owen et al., 2018: CaveCalc: A new model for speleothem chemistry & isotopes',
                'precipitate_mineralogy': 'Alters the precipitate mineralogy. Impacts d13C, d18O, X/Ca, and d44Ca',
          
                
                'co2_decrement': 'Fraction of CO2(aq) removed on each degassing step. Alters the resolution of the evolution of d13C, d44Ca, and X/Ca',
                'calcite_sat_limit': 'Only used when kinetics_mode = ss. CaCO3 only precipitates when saturation index exceeds this value. Impacts d13C, d44Ca, X/Ca and d18O',  
                
                'user_filepath': 'File to users measured data, stored in a timer-series', 


                
                }
            
            font_style = "-size 13 -weight bold" if highlight else "-size 13"
            l = Label(frame, text=header_text, font="-size 13")
            l.grid(row=i,columnspan=2, sticky=SW, pady=3)
            i += 1
            for a, b in self._loop_gen(layout_number):
                color = 'red' if a in ['soil_d13C', 'soil_pCO2', 'cave_pCO2', 'gas_volume','temperature','atm_d18O'] else 'black'
                if b == 'A':   
                    label = Label(frame, text=ns(a), fg=color) 
                    label.grid(row=i, sticky=W) 
                
                    Tooltip(label, tooltips_variables.get(a, 'No information available')) 
                    
                    x = InputsRangeWidget(frame, self.settings[a]) 
                    x.grid(row=i, column=1, sticky=W) 
                    
                    if a == 'atm_d18O': 
                        def convert_to_vpdb(var=self.settings[a]): 
                            try: 
                                # Get the input string and split by commas 
                                vsmow_values = var.get().split() 
                                # Convert each value
                                vpdb_values = [] 
                                for val in vsmow_values: 
                                    val = val.strip() 
                                    if val:  
                                        vsmow = float(val) 
                                        vpdb = (0.970001 * vsmow) - 29.99 
                                        vpdb_values.append(str(round(vpdb, 4)))  
                                var.set(' '.join(vpdb_values)) 
                            except ValueError: 
                                messagebox.showerror("Conversion Error", "Please enter valid δ¹⁸O value(s), separated by commas.") 
                        Button(frame, text="→ VPDB", command=convert_to_vpdb).grid(row=i, column=2, sticky=W)

                elif b == 'B': # text without range
                    label = Label(frame, text=ns(a), fg=color) 
                    label.grid(row=i, sticky=W) 
                    # Add tooltip for variable if available 
                    Tooltip(label, tooltips_variables.get(a, 'No information available'))
                    x = Entry(frame, textvariable=self.settings[a], width=25)
                    x.grid(row=i, column=1, columnspan=2, sticky=W)    
                elif b == 'C': # options menu
                    
                    x = OptsWidget( frame, ns(a), self.settings[a], 
                                    self.units[a], row=i )
                    x.grid(row=i, column=0, sticky=W)
                elif b == 'D': # check button
                    label = Label(frame, text=ns(a), fg=color) 
                    label.grid(row=i, sticky=W) 
                    # Add tooltip for variable if available 
                    Tooltip(label, tooltips_variables.get(a, 'No information available'))
                    r = Checkbutton( frame, variable=self.settings[a],
                                     onvalue=True, offvalue=False )
                    r.grid(row=i, column=1)
                elif b == 'E': # load button
                    label = Label(frame, text=ns(a), fg=color) 
                    label.grid(row=i, sticky=W) 
                    # Add tooltip for variable if available 
                    Tooltip(label, tooltips_variables.get(a, 'No information available'))
                    f = FileFindWidget( frame, value=self.settings[a], 
                                        mode='load')
                    f.grid(row=i, column=1)
                elif b == 'F': # save button
                    label = Label(frame, text=ns(a), fg=color) 
                    label.grid(row=i, sticky=W) 
                    # Add tooltip for variable if available 
                    Tooltip(label, tooltips_variables.get(a, 'No information available'))
                    f = FileFindWidget( frame, value=self.settings[a], 
                                        mode='dir')
                    f.grid(row=i, column=1)
                i += 1
                
            # Add the buttons for "CDA Mode" only if it matches this section 
            if header_text == 'CDA Settings': 
              
                # Create a frame for file paths
                file_paths_frame = Frame(frame)
                file_paths_frame.grid(row=i + 2, column=0, columnspan=3, pady=5)
                
                # Add heading
                heading = Label(file_paths_frame, text="Plot CDA results vs measured data", font="-size 12 -weight bold")
                heading.grid(row=0, column=0, columnspan=2, pady=10)


                # Use FileFindWidget for CDA path
                Label(file_paths_frame, text="CDA results path:").grid(row=2, column=0, sticky=W)
                FileFindWidget(file_paths_frame, value=self.CDA_path, mode='dir').grid(row=2, column=1)

                # Button to trigger plotting
                Button(file_paths_frame, text="Plot", command=self._plot_CDA).grid(row=3, columnspan=3)

                # Button to open help file
                Button(file_paths_frame, text="Help", command=self._show_help).grid(row=5, column=0, columnspan=3, pady=10)
            
            return i
        
        
        def toggle_expand_collapse(section_name): 
            """Toggle the visibility of the expandable frame for a given section."""
            frame = self.expandable_frames.get(section_name) 
            if frame is None: 
                return  # Frame not found 
            if frame.winfo_ismapped(): 
                frame.grid_forget()
                self.toggle_buttons[section_name].config(text=f"▼ {section_name}")
            else: 
                frame.grid(row=row_indices[section_name], column=0, sticky='nsew')
                self.toggle_buttons[section_name].config(text=f"▲ {section_name}")
        
            # Create a dictionary for tooltips
        #tooltips = {
        #'Atmospheric End-member': 'O2 (%), pCO2 (ppmv), d13C (‰) and R14C (pmc) of the atmospheric end-member.',
        #'Soil Gas End-member': 'O2 (%), pCO2 (ppmv), d13C (‰) and R14C (pmc) of the soil gas End-member.',
        #'Mixed Gas': 'Set mixing settings between atmospheric and soil gas end-members.',
        #'Cave Air': 'O2 (%), pCO2 (ppmv), d13C (‰), R14C (pmc), d18O (‰) and volume (L) of cave air.',
        #'Soil Metals (Chloride Salts)': 'X/Ca (mmol/kgw) and d44Ca (‰) of metals within the soil Metals.',
        #'Bedrock Chemistry': 'Lithology, X/Ca (mmol/mol) and d44Ca (‰) of metals within the bedrock.',
        #'Bedrock Dissolution Conditions': 'Amount of bedrock and pyrite (moles), and gas volume (L/kg) during bedrock dissolution ',
        #'General': 'Rainfall d18O (‰, VSMOW), Temperature of cave system (°C), and option for d13C kinetic fractionation',
        #'Additional d18O controls': 'Allow PCarbP to impact d18O, setting the amount of influence',
        #'Aragonite/Calcite Mode': 'Set the mineralogy and database to either calcite or aragonite',
        #'Scripting Options': 'Sets CaveCalc mode, the amount of CO2 removed per degassing step, and defines the supersaturation limit.', 
        #'Additional PHREEQC output': 'Define isotopes, molalities and toals of additional PHREEQC outputs.',
        #'File IO Settings': 'File Input/Output settings.',
        #'CDA Mode': 'Define input file path, tolerance levels. Run and plot CDA.'  
        #}
        
        px = 5 # padding between frames
        py = 2 # padding between frames
        
        # Initialize dictionaries only once
        self.expandable_frames = {}
        self.toggle_buttons = {}
        row_indices = {}

        # Create Frame 1 with collapsible sections

        F1 = Frame(self.master)
        Label(F1, text='', font="-size 12 -weight bold").grid(row=0, columnspan=3)
    

        section_names = [
        ('Atmospheric End-member', 10),
        ('Soil Gas End-member', 11),
        ('Mixed Gas', 12),
        ('Cave Air', 17),
        ('File IO Settings', 4),
        ]
        current_row = 1
        
        
        for section_name, layout_number in section_names:  
            if section_name == 'File IO Settings': 
                # Special case for 'File IO Settings' 
                i = add_things_to_frame(F1, 4, 'File IO Settings', current_row) 
            else: 
                # Add toggle button
                self.toggle_buttons[section_name] = Button(F1, text=f"▼ {section_name}", command=lambda s=section_name: toggle_expand_collapse(s))
                self.toggle_buttons[section_name].grid(row=current_row, column=0, sticky=W) 
                
                # Create expandable frame for the section
                self.expandable_frames[section_name] = Frame(F1) 
                current_row += 1 
                
                # Add section contenrt 
                i = add_things_to_frame(self.expandable_frames[section_name], layout_number, section_name, 0, highlight=True, font="-size 13 -weight bold") 
                row_indices[section_name] = current_row 
                
                # Increment the row for the next section
                current_row += 1

        F1.pack(side='left', fill=Y, anchor='n', padx=px, pady=py)

        # Create Frame 3 with collapsible sections
        F2 = Frame(self.master)
        Label(F2, text='', font="-size 12 -weight bold").grid(row=0, columnspan=3)
    

        section_names = [
        ('Soil Metals (Chloride Salts)', 16),
        ('Bedrock Chemistry', 13),
        ('Bedrock Dissolution Conditions', 14),
        ('General', 15),
        ]
        
        current_row =1
        for section_name, layout_number in section_names: 
            # Add toggle button
            self.toggle_buttons[section_name] = Button(F2, text=f"▼ {section_name}", command=lambda s=section_name: toggle_expand_collapse(s))
            self.toggle_buttons[section_name].grid(row=current_row, column=0, sticky=W)
                      
            # Create tooltip for toggle button
            #Tooltip(self.toggle_buttons[section_name], tooltips.get(section_name, 'No information available'))
            # Create expandable frame for the section
            self.expandable_frames[section_name] = Frame(F2)
            current_row += 1

            # Add section content
            i = add_things_to_frame(self.expandable_frames[section_name], layout_number, section_name, 0, highlight=True, font="-size 13 -weight bold")
            row_indices[section_name] = current_row

            # Increment the row for the next section
            current_row += 1
            
        
        
        F2.pack(side='left', fill=Y, anchor='n', padx=px, pady=py)
        self.F2 = F2

        # Create Frame 3 with collapsible sections
        F3 = Frame(self.master)
        Label(F3, text='', font="-size 12 -weight bold").grid(row=0, columnspan=3)
    

        # Define sections
        sections = [
        ('Aragonite/Calcite Mode', 5),
        ('Scripting Options', 2),
        ('Additional PHREEQC output', 3),
        ('CDA Settings', 1),
        ]

        current_row = 1
        for section_name, layout_number in sections: 
            # Determine button color
            button_color = 'red' if section_name in ['Aragonite/Calcite Mode', 'CDA Mode'] else 'black'

            # Add toggle button
            self.toggle_buttons[section_name] = Button(F3, text=f"▼ {section_name}", command=lambda s=section_name: toggle_expand_collapse(s))
            self.toggle_buttons[section_name].grid(row=current_row, column=0, sticky=W)
           
            # Create tooltip for toggle button
            #Tooltip(self.toggle_buttons[section_name], tooltips.get(section_name, 'No information available'))
           
            # Create expandable frame for the section
            self.expandable_frames[section_name] = Frame(F3)
            current_row += 1

            # Add section content
            i = add_things_to_frame(self.expandable_frames[section_name], layout_number, section_name, 0, highlight=True, font="-size 13 -weight bold")
            row_indices[section_name] = current_row
            
            
            # Increment the row for the next section
            current_row += 1
        
        
        # Add Run button 
        RunButton = Button(F3, text="Run CaveCalc only!", command=lambda: self._run_models()) 
        RunButton.grid(row=i, column=0, sticky=W, padx=0, pady=(35, 1))
        
        RunCDAButton = Button(F3, text="Run CaveCalc with CDA!", command=self.run_models_CDA) 
        RunCDAButton.grid(row=i + 1, column=0, sticky=W, padx=0, pady=1) 
        
     
        # Add link to output GUI
        LinkButton = Button(F3, text="CaveCalc Output", command=lambda: CCAnalyseGUI(Toplevel(self.master)))
        LinkButton.grid(row=i + 2, column=0, sticky=W, padx=0, pady=2)  # Place below the Run buttons
   
        
       
        F3.pack(side='left', anchor='n', padx=px, pady=py)  
        self.F3 = F3
    
    
    def open_CDA_gui(self):
        """Open the CDA GUI window."""
        CDAGUI(Toplevel(self.master), self)   
        
    def _run_models(self):
        
        s = self.settings.copy()
        out_dir = s.pop('out_dir').get()
        d = {}
        
        d1 = {k:v for (k,v) in s.items() if self.get_ln(k) != 'A'}
        d2 = {k:v for (k,v) in s.items() if self.get_ln(k) == 'A'}
        
        d1 = ns(tk2py(d1, parse=False))
        d2 = ns(tk2py(d2, parse=True))
        
        d = {**d1, **d2}

        p = cavecalc.forward_models.ForwardModels(settings=d, 
                                                  output_dir=out_dir)
        p.run_models()
        p.save()
        print("Done.")
    
    # Define the new method to handle the Run button click 
    def confirm_run_rainfall_calculator(self): 
        # Pop-up message asking if d44Ca bedrock is defined 
        response = messagebox.askyesno("Confirm", "Have you defined d44Ca bedrock?")  
        
        if response:   
            self.run_rainfall_calculator()  
        else:  
            messagebox.showinfo("Info", "Please define d44Ca bedrock before proceeding.")  # Optional: Info message if 'No' is clicked

    
    def run_rainfall_calculator(self):  
        s = self.settings.copy()
        out_dir = s.pop('out_dir').get()
        d = {}
        
        d1 = {k:v for (k,v) in s.items() if self.get_ln(k) != 'A'}
        d2 = {k:v for (k,v) in s.items() if self.get_ln(k) == 'A'}
        
        d1 = ns(tk2py(d1, parse=False))
        d2 = ns(tk2py(d2, parse=True))
        
        d = {**d1, **d2}

        p = cavecalc.forward_models.ForwardModels(settings=d, 
                                                  output_dir=out_dir)
        p.rainfall_calculator()
        print("Done.")
        
    def run_models_CDA(self): 
        """Run the CDA models with additional checks."""
    
        # Copy settings
        s = self.settings.copy()
    
        # Check if user_filepath is specified
        user_filepath = s.get('user_filepath').get()  # Access 'user_filepath' from settings
        if not user_filepath: 
            # Show warning popup if user_filepath is empty
            messagebox.showwarning("Warning", "User needs to specify input file in CDA Settings") 
            return  # Exit the method if user_filepath is not specified
    
        out_dir = s.pop('out_dir').get()  # Pop out_dir from settings
        d = {}
    
        # Split settings into two categories based on layout number
        d1 = {k: v for k, v in s.items() if self.get_ln(k) != 'A'}
        d2 = {k: v for k, v in s.items() if self.get_ln(k) == 'A'}
    
        # Convert settings from Tkinter to Python
        d1 = ns(tk2py(d1, parse=False))
        d2 = ns(tk2py(d2, parse=True))
    
        # Merge dictionaries
        d = {**d1, **d2}
    
        # Run models
        p = cavecalc.forward_models.ForwardModels(settings=d, output_dir=out_dir)
        p.run_models()
        p.save()
        print("Done.")     
        
class CDAGUI(object):
    """The CDA GUI window."""
    
     
    def __init__(self, master, cc_input_gui):
        self.master = master
        self.master.title('CDA')
        self.CDA_input_path = StringVar()
        self.CDA_path = StringVar()
        self.file_paths_frame()  # Add the file paths frame
        self.construct_inputs()  # Add the CDA inputs
        
    def file_paths_frame(self): 
        """Frame for inputting file paths for CDA data.""" 
        F2 = Frame(self.master)
        
        # Add heading
        heading = Label(F2, text="Plot CDA results vs measured data", font="-size 12 -weight bold")
        heading.grid(row=0, column=0, columnspan=2, pady=10)

        # Use FileFindWidget for CDA input path
        Label(F2, text="Users input file:").grid(row=1, column=0, sticky=W)
        FileFindWidget(F2, value=self.CDA_input_path, mode='Load').grid(row=1, column=1)

        # Use FileFindWidget for CDA path
        Label(F2, text="CDA.xlsx results Path:").grid(row=2, column=0, sticky=W)
        FileFindWidget(F2, value=self.CDA_path, mode='Load').grid(row=2, column=1)

        # Button to trigger plotting
        Button(F2, text="Plot", command=self._plot_CDA).grid(row=3, columnspan=3)
        
        # Button to open help file
        Button(F2, text="Help", command=self._show_help).grid(row=3, column=2, columnspan=3, pady=10)
        
        F2.pack(side='bottom', anchor='n', padx=5, pady=5)  # Ensure F2 is packed at the top but below F1
    
    
    def _browse_file(self, path_variable):  
       """Opens a file dialog to select a file and sets the given StringVar.""" 
       filename = filedialog.askopenfilename()  
       if filename: 
           path_variable.set(filename)      
    
    def _plot_CDA(self): 
        """Opens the plotting window with the user-provided file paths."""
        dir1 = self.CDA_input_path.get()
        dir2 = self.CDA_path.get()

        if not dir1 or not dir2:
            print("Both file paths are required!")
            return

        try: 
            evaluator = Evaluate()
            print("Plotting...")
            evaluator.plot_CDA(dir1, dir2)
            plt.show(block=False)
            plt.pause(1)
        except Exception as e:  
            print(f"Error while plotting: {e}") 
            
    def _show_help(self): 
        """Opens the CDA_help.txt file in the default text viewer.""" 
        try: 
            # Locate the help file within the cavecalc.gui package using importlib.resources 
            with importlib.resources.path(cavecalc.gui, 'CDA_help.txt') as help_file_path: 
                help_file_path_str = str(help_file_path)  # Convert PosixPath to string
            
                # Open the file with the default application
                if subprocess.os.name == 'nt':  # For Windows 
                   subprocess.run(['start', help_file_path_str], shell=True) 
                elif subprocess.os.name == 'posix':  # For macOS and Linux 
                     if 'darwin' in subprocess.os.uname().sysname.lower():  # For macOS 
                         subprocess.run(['open', help_file_path_str])
                     else:  # For Linux 
                         subprocess.run(['xdg-open', help_file_path_str])
                else: 
                    print("Unsupported operating system for opening help files.")
        except Exception as e: 
            print(f"Error while opening help file: {e}")
            
      
    def _open_file(self, file_path): 
        """Opens a file with the default application based on the operating system."""
        try: 
            # Open the file with the default application 
            if subprocess.os.name == 'nt':  # For Windows 
               subprocess.run(['start', file_path], shell=True) 
            elif subprocess.os.name == 'posix':  # For macOS and Linux 
                 if 'darwin' in subprocess.os.uname().sysname.lower():  # For macOS 
                    subprocess.run(['open', file_path])
                 else:  # For Linux
                    subprocess.run(['xdg-open', file_path])
            else: 
                print("Unsupported operating system for opening files.")
        except Exception as e: 
            print(f"Error while opening file: {e}")  

        
class CCAnalyseGUI(object):
    """The Cavecalc Output GUI window."""
    
    def __init__(self, master):
        self.master = master
        self.master.title('Cavecalc Output GUI')
        self.e = Evaluate()
        self.dir = StringVar()
        self.dir.set(os.getcwd())
        self.loaded_dirs = []
        self.dnum = IntVar() # total no of models loaded
        self.dnum.set(0)
        self.settings_report = {}
        
        # File paths for the CDA
        self.CDA_input_path = StringVar()
        self.CDA_path = StringVar()
        
        self.load_outputs_frame()
        self.save_buttons_frame()
        #self.file_paths_frame()  # Adding the file path input frame
        
       
        
    def _csv_dir_save(self):
        d = filedialog.askdirectory()
        if d:
            self.e.save_csvs(d)
        
    def _mat_save(self):
        d = filedialog.asksaveasfilename()
        if d:
            self.e.save_all_mat(file=d)
            
    def _add_data(self):
        """Loads data from the currently selected directory."""
        d = filedialog.askdirectory()
        
        if d:
            if d not in self.loaded_dirs:
                self.e.load_data(d)
                self.dnum.set(len(self.e.model_results))
                self.loaded_dirs.append(d)
        
    def load_outputs_frame(self):
        F0 = Frame(self.master)
        
        b = Button(master=F0, text="Load Model Output",
                   command = lambda : self._add_data())
        b.grid(row=0, column=0, columnspan=2)
        
        Label(F0, text="Models Loaded").grid(row=1, column=0, sticky=W)
        
        t1 = Entry(master=F0, textvariable=self.dnum, state='readonly')
        t1.grid(row=1,column=1)        
        F0.pack()
                  
    def save_buttons_frame(self):
        F1 = Frame(self.master)
        
        b1 = Button(master=F1, text="save as .csv", 
                    command = lambda : self._csv_dir_save())
        b1.grid(row=0, column=0)
        b2 = Button(master=F1, text="save as .mat", 
                    command = lambda : self._mat_save())
        b2.grid(row=0, column=1)
        b3 = Button(master=F1, text='Open Plotting Window',
                    command = lambda : PlottingWindow(self))
        b3.grid(row=0, column=2)
        
        F1.pack()
        
     


        
class PlottingWindow(Toplevel):
    def __init__(self, CCAnalyseGUI):
        super().__init__(CCAnalyseGUI.master)
        self.title('Cavecalc Plotting')
        
        
        self.e = CCAnalyseGUI.e
        self.b = Evaluate()
        self.o = self.e.model_results[0]
        self.s = self.e.model_settings[0]
        self.report = self.e.get_settings_report()
        
        lx = Label(self, text = "X variable (Required)")
        ly = Label(self, text = "Y variable (Required)")
        ll = Label(self, text = "Label with (Optional)")
        X_Sel, self.x = self.OutputSelectWidget()
        Y_Sel, self.y = self.OutputSelectWidget()
        L_Sel, self.l = self.SettingSelectWidget()
        
        lx.grid(row=0, column=0, sticky=W)
        X_Sel.grid(row=0, column=1)
        ly.grid(row=1, column=0, sticky=W)
        Y_Sel.grid(row=1, column=1)
        ll.grid(row=2, column=0, sticky=W)
        L_Sel.grid(row=2, column=1)
        
        # Radiobutton selector for data filtering (for plot)
        self.v = IntVar()
        self.v.set(0)
        r0 = Radiobutton(   self, text="Full Model (inc. initial solution)", 
                            variable=self.v, value=0)
        r1 = Radiobutton(   self, text="Full Model (excl. inital solution)", 
                            variable=self.v, value=1)
        r2 = Radiobutton(   self, text="Bedrock Dissolution Solution only", 
                            variable=self.v, value=2)
        r3 = Radiobutton(   self, text="End Point Solution only", 
                            variable=self.v, value=3)
        r4 = Radiobutton(   self, text="Precipitation Steps only",
                            variable=self.v, value=4)
                            
                            
        r0.grid(row=3)
        r1.grid(row=4)
        r2.grid(row=6)
        r3.grid(row=7)
        r4.grid(row=5)
                            
        b = self.PlotButton()
        b.grid(row=8,columnspan=2)

    def SettingSelectWidget(self):
        v = StringVar()
        opt = list(self.report.keys())
        if HIDDEN_OPTS:
            opt = [o for o in opt if o not in HIDDEN_OPTS]
        
        o = []
        for entry in opt:
            try:
                o.append(ns(entry))
            except KeyError:
                o.append(entry)
        return OptionMenu(self, v, *sorted(o)), v
        
    def OutputSelectWidget(self):
        v = StringVar()
        opt = list(self.o.keys())
        return OptionMenu(self, v, *sorted(opt)), v
    
    def PlotButton(self):

        b = Button(self, text='Plot Graph', 
                    command = lambda : self.plot())
        return b
        
    def plot(self): 

        if self.v.get() == 1:
            a = self.e.filter_by_index(ind=0, n=True)
        elif self.v.get() == 2:
            a = self.e.filter_by_index(ind=1)
        elif self.v.get() == 3:
            a = self.e.filter_by_index(ind=-1)
        elif self.v.get() == 4:
            a = self.e.filter_by_results('step_desc', 'precip')
            
            
        else:
            a = copy.deepcopy(self.e)
           
        f = lambda x : None if x == '' else x
        x_lab = f(self.x.get())
        y_lab = f(self.y.get())
        lab_name = f(self.l.get())
        
        x = []
        y = []
        for v in a.model_results:
            x.append(v[x_lab])
            y.append(v[y_lab])
        
        if lab_name:
            labs = [s[ns(lab_name)] for s in a.model_settings]       
        else:
            labs = None
        
        print("Plotting...")
        gplot( x, y, x_lab, y_lab, labs, lab_name )
        
if __name__ == '__main__':
    CCInputGUI()
    # CCAnalyseGUI()
