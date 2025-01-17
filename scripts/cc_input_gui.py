try:
    import tkinter as tk
    from cavecalc.gui.gui import CCInputGUI
    tkinter_available = True
except ImportError:
    tkinter_available = False
    import streamlit as st
    from cavecalc.gui.gui_web import StreamlitCCInputGUI  # Adjust this import for your Streamlit GUI

def run_tkinter():
    """Run Tkinter GUI."""
    root = tk.Tk()
    app = CCInputGUI(root)
    root.mainloop()

def run_streamlit():
    """Run Streamlit GUI."""
    st.title('Cavecalc Streamlit GUI')
    app = StreamlitCCInputGUI()
    app.show_gui()  # Replace this with your Streamlit logic (similar to how you did for PlottingWindow)

if __name__ == '__main__':
    if tkinter_available:
        run_tkinter()
    else:
        run_streamlit()
