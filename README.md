# KiCadToLTspice
A python script that interface KiCad to LTspice.

This script allows you to :
- configure simulation ac, dc, transient, op,
- adjust parameters for parametric simulation,
- configure spice netlist for Monte Carlo and Worst Case analysis.

# Installation
## On Windows
1. Install Python 3.8 or above (with the Microsoft Store or https://www.python.org/downloads/windows/)
2. Install the Github Project in your Documents path (spaces are not allowed in this path name)
If username contains spaces, put the project in another directory without space in the path. Then edit the first line of the KicadToLTspice.bat and change C:/Users/%username%/Documents/KiCadToLTspice/ by the path of the project.
3. Configure LTspice Library Search path :
- run LTspice
- select Menu Tools -> Control Panel
- add the path to the ModelsForKicad in the Library Search section (for example : C:\Users\username\Documents\KiCadToLTspice\libForKicad\ModelsForKicad where username is your windows user name).
4. Add **KiCadToLTspice\libForKicad\** libraries in the KiCad symbol editor.

## On Mac OS X - Linux
Python script must be adapted.
Contact me if you do it.




