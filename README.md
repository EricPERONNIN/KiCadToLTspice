# KiCadToLTspice
A python script that interface KiCad to LTspice.

This script allows you to :
- configure ac, dc, transient and op simulation,
- adjust parameters for parametric simulation,
- configure spice netlist for Monte Carlo and Worst Case analysis.

# Prerequisites
**KiCad installed** (see https://kicad-pcb.org/download/windows/).
**LTspiceXVII installed** (https://www.analog.com/en/design-center/design-tools-and-calculators/ltspice-simulator.html).
**Python 3 installed** (Windows Store or https://www.python.org/downloads/windows/).

# Installation
## On Windows
1. Download project zip file from here and extract it in your Documents directory (spaces are not allowed in this path name)
If username contains spaces, put the project in another directory without space in the path. Then edit the first line of the KicadToLTspice.bat and change C:/Users/%username%/Documents/KiCadToLTspice/ by the path of the project.
2. Configure LTspice Library Search path :
- run LTspice
- select Menu Tools -> Control Panel
- in the Library Search section, add path to the ModelsForKicad which is located in the directory \libForKicad\ModelsForKicad within KiCadToLTspice directory  (for example : C:\Users\\**username**\Documents\KiCadToLTspice\libForKicad\ModelsForKicad where username is your windows user name).
3. Add **KiCadToLTspice\libForKicad\** libraries in the KiCad symbol editor.

# Script configuration
- Run the script in a command windows by **start pythonw3 KicadToLTspice.py**
- In the configuration tab, feed the **LTspice executable file** field and the LTspice Libraries Directory (usualy C:/Users/**username**/Documents/LTspiceXVII)

# How to execute the Script ?
A. In a command windows by **start pythonw3 KicadToLTspice.py** (just to manage libraries and configure Script).
B. From KiCad :
- Tools -> Generate Netlist File...
- Select Spice Tab
- In the simulator command : point to the KicadToLTspice.bat file (example : C:/Users/**username**/Documents/KiCadToLTspice/KicadToLTspice.bat)

## On Mac OS X - Linux
Script must be adapted for Mac OS X and Linux.
Contact me when you will have done this.




