import os
import copy
import subprocess
import numpy as np
import importlib
import matplotlib.pyplot as plt
import streamlit as st
from collections import OrderedDict
from cavecalc.analyse import Evaluate
import cavecalc.data.types_and_limits
from cavecalc.setter import SettingsMaker, NameSwitcher, SettingsObject
import time

# settings options hidden from plotting menus (useless clutter)
HIDE_OPS = True
HIDDEN_OPTS = [
    'totals',  'molalities',   'isotopes',     'out_dir', 
    'phreeqc_log_file',        'phreeqc_log_file_name',
    'database']  # options not available for plotting

ns = NameSwitcher()

def od(dict):
    """Converts a dict to an ordered dict, sorted by key."""
    return OrderedDict(sorted(dict.items()))

def py2tk(dict):
    """Convert a dictionary to Streamlit-compatible types.
    
    Convert dictionary entries from doubles and strings to strings for use 
    with Streamlit. Returns a modified copy.
    """
    out = copy.copy(dict)
    for k in dict.keys():
        if dict[k] is not None:
            out[k] = str(dict[k])
        else:
            out[k] = None
    return out

def _parse_value_input(string, allow=[]):
    """
    Parses input to detect ranges of values or single values.
    Returns either a single value or a list of values.
    """
    a = string
    
    # remove brackets
    rm = ['(', ')', '[', ']']
    for s in rm:
        if s not in allow:
            a = a.replace(s,'')
    
    # replace commas with space
    a = a.replace(',',' ')
    
    # split string on spaces
    a = a.split(' ')
    
    # attempt conversion to float
    try:
        b = [float(v) for v in a if v != '']
    except ValueError:
        b = [str(v) for v in a if v != '']
    
    # remove list structure from single entries
    if len(b) == 1:
        b = b[0]
    
    return b

def tk2py(dict, parse=False):
    """Inverse of py2tk.
    
    Convert a dict of Streamlit-compatible types to a dict understandable by
    the cavecalc setter module.
    
    Args:
        dict: A dict full of GUI inputs (e.g., string types)
        parse (optional): If True, process numeric input to get a list of
            values if possible. Default False.
    Returns:
        A dictionary of booleans, strings, lists, and floats.
    """    
    
    a = dict.copy()
    for k in dict.keys():
        if dict[k] is None:
            a[k] = None
        elif isinstance(dict[k], str):
            if parse:
                a[k] = _parse_value_input(dict[k])
            else:
                a[k] = dict[k]
        else:
            a[k] = dict[k]
        
    b = {k:v for k,v in a.items() if v is not None}
    return b

def gplot(x_values, y_values, x_label, y_label, label_vals, label_name):
    """Plot data in a Streamlit-compatible format."""
    
    fig, ax = plt.subplots()
    
    # if plotting a single point from each model
    if all(len(x) == 1 for x in x_values):
        xs = [x[0] for x in x_values]
        ys = [y[0] for y in y_values]
        
        ax.plot(xs, ys, 'x--')
        
        if label_name:
            for label, x, y in zip(label_vals, xs, ys):
                ax.annotate("%s=%s" % (label_name, label), xy=(x, y), fontsize=8)
        plt.ylabel(y_label)
        plt.xlabel(x_label)
        
        st.pyplot(fig)
     
    # else plot each model as its own series
    else:
        for (i, xs) in enumerate(x_values):
            ys = y_values[i]
            if label_name:
                l_str = "%s: %s" % (label_name, label_vals[i])
                ax.plot(xs, ys, label=l_str)
                ax.legend(prop={'size':8})
            else:
                ax.plot(xs, ys)
            
        plt.ylabel(y_label)
        plt.xlabel(x_label)
        
        st.pyplot(fig)

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None

    def show_tooltip(self):
        # Use Streamlit's st.tooltip for the widget that we want to show a tooltip for
        st.tooltip(self.text)


class FileFindWidget:
    """A Streamlit Widget for opening a file browser window."""
    
    def __init__(self, value=None, mode=None):
        self.value = value
        self.mode = mode

        # Display the file path entry
        self.entry = st.text_input("File Path", value=self.value)
        
        if self.mode.capitalize() == 'Load':
            self.button = st.file_uploader("Browse to load", type=None)
        elif self.mode.capitalize() == 'Save':
            # Streamlit does not have a direct "save as" dialog, so we use file uploader workaround
            self.button = st.text_input("Save file as (manual input)", "")
        elif self.mode.capitalize() == 'Dir':
            # No native Streamlit support for directory browsing
            self.button = st.text_input("Directory Path", "")
        else:
            raise ValueError("Mode %s not recognised. Use save, load, or dir." % self.mode)

        # Handle file selection
        if self.mode.capitalize() == 'Load' and self.button:
            if self.button:
                self.value = self.button.name
                self.entry = st.text_input("File Path", self.value)  # Update the entry with selected file

        if self.mode.capitalize() == 'Save' and self.button:
            if self.button:
                self.value = self.button
                self.entry = st.text_input("Save file as", self.value)  # Update the entry with the filename

        if self.mode.capitalize() == 'Dir' and self.button:
            if self.button:
                self.value = self.button
                self.entry = st.text_input("Directory Path", self.value)  # Update the entry with the selected directory

class InputsRangeWidget:
    """A compound widget for inputting a range of numeric values."""

    def __init__(self, value=None):
        self.value = value
        self.min_val = None
        self.max_val = None
        self.steps = None

    def display(self):
        """Displays the widget and allows input for the range."""

        # Text input for the value (which could be a list of values)
        self.value = st.text_input("Input Values", value=str(self.value))

        # Display 'Set Range' button
        if st.button('*'):
            self.select_range()

    def select_range(self):
        """Generates a range using user-provided min, max, and steps."""
        
        # Input fields for min, max, and steps
        self.min_val = st.number_input("Min Value", value=0.0, format="%.6f")
        self.max_val = st.number_input("Max Value", value=10.0, format="%.6f")
        self.steps = st.number_input("Steps", value=5, min_value=1, step=1)

        # Button to generate range
        if st.button("Generate Range"):
            try:
                # Generate the range using linspace
                vals = np.linspace(self.min_val, self.max_val, self.steps)
                self.value = vals.tolist()
                st.write("Generated Range:", self.value)
            except ValueError as e:
                st.error(f"Error: {e}. Ensure all inputs are numbers.")
            except TypeError as e:
                st.error(f"Error: {e}. Ensure 'steps' is an integer.")

class OptsWidget:
    """A widget for selecting from a list of options."""
    
    def __init__(self, parameter, value, options):
        self.parameter = parameter
        self.value = value
        self.options = options
        
        # Check that options are a list
        assert isinstance(options, list)
        
    def display(self):
        """Display the parameter label and options menu."""
        
        # Label for the parameter
        st.write(f"{self.parameter}:")
        
        # Dropdown (selectbox) for options
        self.value = st.selectbox(self.parameter, self.options, index=self.options.index(self.value) if self.value in self.options else 0)
        
        return self.value  # Return the selected value


class InputsWidget:
    """A widget for inputting a value."""
    
    def __init__(self, parameter, value):
        self.parameter = parameter
        self.value = value
        
    def display(self):
        """Display the parameter label and text input."""
        
        # Label for the parameter
        st.write(f"{self.parameter}:")
        
        # Text input field
        self.value = st.text_input(self.parameter, value=self.value)
        
        return self.value  # Return the input value

class CCInputStreamlit:
    """The Cavecalc input Streamlit interface."""

    def __init__(self):
        """Initialize the main Streamlit GUI."""
        self.settings = None
        self.d = SettingsObject()

        # Load defaults
        self._load_defaults()

    def _load_defaults(self):
        """Load default settings and variables."""
        self.units = vars(cavecalc.data.types_and_limits).copy()
        self.layout = vars(cavecalc.gui.layout).copy()

        settings = self.d.dict()
        self.settings = settings  # Replacing py2tk() since it might be unnecessary in Streamlit

    def _show_loading_screen(self):
        """Display a loading screen with a welcome message."""
        st.write("Welcome to CaveCalc v2.0")
        st.write("Always go feet first into CaveCalc")

    def _browse_file(self):
        """Replaces the Tkinter file dialog with Streamlit file uploader."""
        uploaded_file = st.file_uploader("Upload your file", type=["csv", "txt", "xlsx"])
        if uploaded_file is not None:
            return uploaded_file
        else:
            st.warning("No file uploaded yet.")
            return None

    def _plot_CDA(self):
        """Opens the plotting window with the user-provided file paths."""
        dir1 = self.settings.get('user_filepath', '')
        dir2 = self.CDA_path

        if not dir1 or not dir2:
            st.error("Both file paths are required!")
            return

        try:
            evaluator = Evaluate()
            st.write("Plotting...")
            evaluator.plot_CDA(dir1, dir2)
            plt.show(block=False)
            plt.pause(1)
        except Exception as e:
            st.error(f"Error while plotting: {e}")

    def _show_help(self):
        """Display the help file."""
        try:
            # Locate the help file within the cavecalc.gui package
            with importlib.resources.path(cavecalc.gui, 'CDA_help.txt') as help_file_path:
                help_file_path_str = str(help_file_path)
                if subprocess.os.name == 'nt':  # For Windows
                    subprocess.run(['start', help_file_path_str], shell=True)
                elif subprocess.os.name == 'posix':  # For macOS and Linux
                    if 'darwin' in subprocess.os.uname().sysname.lower():  # For macOS
                        subprocess.run(['open', help_file_path_str])
                    else:  # For Linux
                        subprocess.run(['xdg-open', help_file_path_str])
                else:
                    st.error("Unsupported operating system for opening help files.")
        except Exception as e:
            st.error(f"Error while opening help file: {e}")
            
    def construct_inputs(self):
        """Construct input widgets for the Streamlit interface."""
        
        def add_things_to_frame(layout_number, header_text, i, highlight=False, font=None):
            # Set the header style if highlighted
            header_style = '###' if highlight else '##'
            st.markdown(f"{header_style} {header_text}")

            # Tooltip variables (simplified for brevity)
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

            # Loop through the layout, similar to how it was handled in Tkinter
            for a, b in self._loop_gen(layout_number):
                color = 'red' if a in ['soil_d13C', 'soil_pCO2', 'cave_pCO2', 'gas_volume', 'temperature', 'atm_d18O'] else 'black'

                # Handle different types of input elements
                if b == 'A':  # Range input
                    st.markdown(f"**{a}:**")
                    st.info(tooltips_variables.get(a, 'No information available'))
                    self.settings[a] = st.slider(a, min_value=0, max_value=100, value=self.settings[a])

                elif b == 'B':  # Text input without range
                    st.markdown(f"**{a}:**")
                    st.info(tooltips_variables.get(a, 'No information available'))
                    self.settings[a] = st.text_input(a, value=self.settings[a])

                elif b == 'C':  # Dropdown (options menu)
                    st.markdown(f"**{a}:**")
                    st.info(tooltips_variables.get(a, 'No information available'))
                    self.settings[a] = st.selectbox(a, options=self.units[a], index=self.units[a].index(self.settings[a]))

                elif b == 'D':  # Checkbox
                    st.markdown(f"**{a}:**")
                    st.info(tooltips_variables.get(a, 'No information available'))
                    self.settings[a] = st.checkbox(a, value=self.settings[a])

                elif b == 'E':  # Load button
                    st.markdown(f"**{a}:**")
                    st.info(tooltips_variables.get(a, 'No information available'))
                    self.settings[a] = st.file_uploader("Upload File", type="csv")

                elif b == 'F':  # Save button
                    st.markdown(f"**{a}:**")
                    st.info(tooltips_variables.get(a, 'No information available'))
                    self.settings[a] = st.text_input("Save file to", value=self.settings[a])

                i += 1

            # Add specific buttons only for CDA mode
            if header_text == 'CDA Settings':
                # File path options for CDA
                st.markdown("### Plot CDA results vs measured data")
                st.text(f"CDA results path: {self.CDA_path}")
                if st.button("Plot"):
                    self._plot_CDA()

                # Help button
                if st.button("Help"):
                    self._show_help()

            return i
        
        def toggle_expand_collapse(section_name): 
            """Toggle the visibility of the expandable section for a given section.""" 
            # In Streamlit, expanders automatically handle this 
            pass  # Streamlit handles collapsible sections with st.expander()

        def app(): 
            # Padding (Streamlit doesn't use px, py like Tkinter, we manage it via layout) 
            px = 5 
            py = 2 
            
            # Initialize a list of sections and layout numbers (same as the section_names in Tkinter) 
            section_names_1 = [ 
                ('Atmospheric End-member', 10),
                ('Soil Gas End-member', 11),
                ('Mixed Gas', 12),
                ('Cave Air', 17),
                ('File IO Settings', 4),
                ] 
            
            section_names_2 = [
                ('Soil Metals (Chloride Salts)', 16),
                ('Bedrock Chemistry', 13),
                ('Bedrock Dissolution Conditions', 14),
                ('General', 15),
                ] 
            
            section_names_3 = [ 
                ('Aragonite/Calcite Mode', 5), 
                ('Scripting Options', 2), 
                ('Additional PHREEQC output', 3), 
                ('CDA Settings', 1), 
                ] 
            
            # Streamlit equivalent of Tkinter Frames (sections wrapped in columns)
            st.title('CDA') 
            
            # Frame 1 (Section 1)
            with st.container(): 
                st.markdown('### Frame 1: Main Sections') 
                for section_name, layout_number in section_names_1: 
                    with st.expander(f"▼ {section_name}"): 
                        # Replace with Streamlit's code to add content 
                        add_things_to_frame(layout_number, section_name) 
                        
            # Frame 2 (Section 2)
            with st.container(): 
                st.markdown('### Frame 2: Soil and Bedrock Sections')
                for section_name, layout_number in section_names_2:
                    with st.expander(f"▼ {section_name}"):
                        # Replace with Streamlit's code to add content
                        add_things_to_frame(layout_number, section_name)

            # Frame 3 (Section 3)
            with st.container(): 
                st.markdown('### Frame 3: Additional Options')
                for section_name, layout_number in section_names_3:
                    with st.expander(f"▼ {section_name}"):
                        # Replace with Streamlit's code to add content
                        add_things_to_frame(layout_number, section_name)

            # Add Run buttons (Streamlit's version)
            st.button("Run CaveCalc only!", on_click=_run_models)
            st.button("Run CaveCalc with CDA!", on_click=run_models_CDA)

            # Add link to output GUI
            st.button("CaveCalc Output", on_click=lambda: CCAnalyseGUI())
            
            
        def open_CDA_gui(self): 
            """Open the CDA GUI window."""
            # Placeholder for the actual CDA GUI opening logic
            st.write("CDA GUI would open here.")
        
        def _run_models(self): 
            """Run the models using the settings provided.""" 
            settings = self.settings.copy() 
            out_dir = settings.pop('out_dir') 
            d = {} 
                
            # Split settings into two categories based on some condition (simulated here) 
            d1 = {k: v for k, v in settings.items() if self.get_ln(k) != 'A'} 
            d2 = {k: v for k, v in settings.items() if self.get_ln(k) == 'A'}

            # Here, you would convert the data if needed (e.g., tk2py conversion)
            d1 = self.ns(self.tk2py(d1, parse=False))
            d2 = self.ns(self.tk2py(d2, parse=True))
        
            # Combine the dictionaries
            d = {**d1, **d2}

            # Here, instantiate your forward models class (assuming `cavecalc` is available)
            p = self.run_forward_models(d, out_dir)
            p.run_models()
            p.save()
            st.success("Models ran successfully.")            


        def run_models_CDA(self): 
            """Run the CDA models with additional checks."""
            settings = self.settings.copy()
        
            # Check if user_filepath is specified
            user_filepath = settings.get('user_filepath')
            if not user_filepath: 
                st.warning("User needs to specify input file in CDA Settings")
            return

            out_dir = settings.pop('out_dir')
            d = {}

            # Split settings into two categories
            d1 = {k: v for k, v in settings.items() if self.get_ln(k) != 'A'}
            d2 = {k: v for k, v in settings.items() if self.get_ln(k) == 'A'}

            # Convert settings if needed
            d1 = self.ns(self.tk2py(d1, parse=False))
            d2 = self.ns(self.tk2py(d2, parse=True))

            # Combine dictionaries
            d = {**d1, **d2}

            # Run models
            p = self.run_forward_models(d, out_dir)
            p.run_models()
            p.save()
            st.success("CDA models ran successfully.")
        
        
class CDAGUI:
    """The CDA GUI window in Streamlit."""
    
    def __init__(self, cc_input_gui):
        self.cc_input_gui = cc_input_gui
        self.CDA_input_path = None
        self.CDA_path = None
        self.show_gui()

    def show_gui(self):
        """Show the CDA interface in Streamlit."""
        
        # Add heading
        st.title('CDA')

        # File uploader for CDA input path
        st.subheader("File Paths")
        self.CDA_input_path = st.file_uploader("Users input file", type=['xlsx', 'csv'])
        self.CDA_path = st.file_uploader("CDA.xlsx results Path", type=['xlsx'])
        
        # Button to trigger plotting
        if st.button("Plot"):
            self._plot_CDA()

        # Button to show help
        if st.button("Help"):
            self._show_help()

    def _plot_CDA(self):
        """Opens the plotting window with the user-provided file paths."""
        if not self.CDA_input_path or not self.CDA_path:
            st.error("Both file paths are required!")
            return

        try: 
            evaluator = Evaluate()
            st.write("Plotting...")
            evaluator.plot_CDA(self.CDA_input_path, self.CDA_path)
            st.pyplot(plt)
        except Exception as e:  
            st.error(f"Error while plotting: {e}")
            
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
                    st.error("Unsupported operating system for opening help files.")
        except Exception as e: 
            st.error(f"Error while opening help file: {e}")
            

class CCAnalyseGUI:
    """The Cavecalc Output GUI window in Streamlit."""
    
    def __init__(self):
        self.e = Evaluate()
        self.loaded_dirs = []
        self.dnum = 0  # Total number of models loaded
        self.settings_report = {}

        # File paths for the CDA
        self.CDA_input_path = None
        self.CDA_path = None
        
        self.show_gui()

    def show_gui(self):
        """Show the GUI in Streamlit."""
        
        # Add title
        st.title('Cavecalc Output GUI')

        # Button to load model output
        if st.button("Load Model Output"):
            self._add_data()

        # Display the number of models loaded
        st.subheader("Models Loaded")
        st.write(f"Total models loaded: {self.dnum}")

        # Buttons to save data
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Save as .csv"):
                self._csv_dir_save()
        with col2:
            if st.button("Save as .mat"):
                self._mat_save()
        with col3:
            if st.button('Open Plotting Window'):
                # Assuming PlottingWindow is a function that can be triggered from here
                self._open_plotting_window()

    def _csv_dir_save(self):
        """Save the model outputs as .csv."""
        dir_path = st.text_input("Choose directory to save CSVs:", value=os.getcwd())
        if dir_path:
            self.e.save_csvs(dir_path)

    def _mat_save(self):
        """Save the model outputs as .mat."""
        file_path = st.text_input("Choose file to save as .mat:", value="")
        if file_path:
            self.e.save_all_mat(file=file_path)
            
    def _add_data(self):
        """Loads data from the currently selected directory."""
        dir_path = st.text_input("Choose directory to load model data from:", value="")
        if dir_path:
            if dir_path not in self.loaded_dirs:
                self.e.load_data(dir_path)
                self.dnum = len(self.e.model_results)
                self.loaded_dirs.append(dir_path)
                st.success(f"{self.dnum} models loaded from {dir_path}")
            else:
                st.warning("This directory has already been loaded.")

    def _open_plotting_window(self):
        """Opens the plotting window. Assuming this function is defined elsewhere."""
        # Here you can call the PlottingWindow logic as needed.
        st.write("Opening Plotting Window... (This can be implemented separately)")

class PlottingWindow:
    def __init__(self, CCAnalyseGUI):
        self.e = CCAnalyseGUI.e
        self.b = Evaluate()
        self.o = self.e.model_results[0]
        self.s = self.e.model_settings[0]
        self.report = self.e.get_settings_report()

        # Streamlit UI components
        self.show_gui()

    def show_gui(self):
        """Show the GUI in Streamlit."""
        # X and Y variable selection
        st.header("Select Variables for Plotting")
        x_var = self.OutputSelectWidget("X variable (Required)", self.o)
        y_var = self.OutputSelectWidget("Y variable (Required)", self.o)
        label_var = self.SettingSelectWidget("Label with (Optional)")

        # Radiobutton selector for data filtering
        filter_option = st.radio(
            "Select Data for Plotting",
            ("Full Model (inc. initial solution)",
             "Full Model (excl. initial solution)",
             "Bedrock Dissolution Solution only",
             "End Point Solution only",
             "Precipitation Steps only"),
            index=0  # Default to "Full Model (inc. initial solution)"
        )

        # Plot button
        if st.button("Plot Graph"):
            self.plot(x_var, y_var, label_var, filter_option)

    def SettingSelectWidget(self, label):
        """Create a dropdown widget for settings selection."""
        options = list(self.report.keys())
        if 'HIDDEN_OPTS' in globals():  # If HIDDEN_OPTS is defined
            options = [o for o in options if o not in HIDDEN_OPTS]

        selected = st.selectbox(label, options)
        return selected

    def OutputSelectWidget(self, label, options):
        """Create a dropdown widget for output variable selection."""
        selected = st.selectbox(label, sorted(options.keys()))
        return selected

    def plot(self, x_var, y_var, label_var, filter_option):
        """Plot the graph based on the selected variables and filter option."""
        # Filter data based on the selected filter option
        if filter_option == "Full Model (excl. initial solution)":
            a = self.e.filter_by_index(ind=0, n=True)
        elif filter_option == "Bedrock Dissolution Solution only":
            a = self.e.filter_by_index(ind=1)
        elif filter_option == "End Point Solution only":
            a = self.e.filter_by_index(ind=-1)
        elif filter_option == "Precipitation Steps only":
            a = self.e.filter_by_results('step_desc', 'precip')
        else:
            a = copy.deepcopy(self.e)

        # Handle empty values for labels
        def f(x): return None if x == '' else x
        x_label = f(x_var)
        y_label = f(y_var)
        label_name = f(label_var)

        # Extract the data for plotting
        x = [v[x_label] for v in a.model_results]
        y = [v[y_label] for v in a.model_results]

        # Optional labels for the plot
        if label_name:
            labels = [s[ns(label_name)] for s in a.model_settings]
        else:
            labels = None

        # Plotting logic (you can implement a custom plot function here)
        st.write("Plotting...")
        self.gplot(x, y, x_label, y_label, labels, label_name)

    def gplot(self, x, y, x_label, y_label, labels, label_name):
        """Plotting function (can be modified for your custom plot)."""
        # Replace this with your plotting logic
        st.write(f"Plotting {x_label} vs {y_label}...")
        # Example: Display a simple line plot for now
        st.line_chart({'x': x, 'y': y})
        