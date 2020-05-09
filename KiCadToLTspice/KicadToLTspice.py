# -*- coding: utf-8 -*-
from tkinter import *
from tkinter import ttk
import sys, os, shutil
import codecs
from tkinter import filedialog 
import json
from tkinter.messagebox import *
import os.path
import re
from threading import Timer
import lib_LTspice2Kicad

DEBUG = False

dataConfig = ""
netlist = []
parameters = [["Global Temperature", "27", "0", "", "", "", ""]]
#previousParameters = [["Global Temperature", "27", "0", "", "", "", ""]]

# App Directory
appDir = "./"
#LTspice Application Data Path
LTspiceExePath = "C:/Program Files/LTC/LTspiceXVII/XVIIx64.exe"
# Point to LTspice document directory
LTspiceDocPath = "c:/Users/" + os.environ['username'] + "/Documents/LTspiceXVII/"
# CIR Project Path
CIRprojectDirectory = ""
CIRfileName = ""

#for i = 0 to sys.argv.count:
sysarg = ' '. join(str(elem) for elem in sys.argv)
if DEBUG: print("Command line : " + sysarg)

monAppli = Tk()
monAppli.title("Kicad to LTspice")
# Get fileName from argv
if len(sys.argv) > 1:
    fichierCIR = sys.argv[1]
    netlistExist = True
    #
    if DEBUG: print("Nom du fichier CIR : " + fichierCIR )
    CIRprojectDirectory = os.path.dirname(fichierCIR)
    CIRfileName = os.path.basename(fichierCIR)
else:
    # showerror("CIR missing file", "Run application with a CIR file in command line")
    netlistExist = False    

def isNativeLTspiceModelLib(libName):
    # Search if libName is in the LTspice sub directory
    if os.path.isfile(LTspiceDocPath + "lib/sub/" + libName):
        return True
    else:
        return False

def getNetlist():
    global netlist
    global parameters

    # Previous parameters
    previousParameters = []
    if os.path.isfile(CIRprojectDirectory + '/parameters.txt'):
        with open(CIRprojectDirectory + '/parameters.txt', 'r') as f:
            lines = f.readlines()
            f.close()
        for line in lines:
            line = line.replace("\n", "")
            if len(line) > 0:
                lineSplit = line.split(",")
                if len(lineSplit) == 7:
                    previousParameters.append(lineSplit)
    else:
        previousParameters = [["Global Temperature", "27", "0", "", "", "", ""]]

    if DEBUG: print(previousParameters)

    parameters = []
    parameters.append(previousParameters[0])

    #Nom du fichier de sortie à partir du nom du fichier d'entrée
    #Ouverture du fichier CIR Kicad
    fichierIn = open(fichierCIR, 'r')
    #Copie du fichier d'entrée jusqu'au .end
    lines = fichierIn.readlines()
    netlist = []
    for line in lines:
        #if DEBUG: print("ext:"+line.capitalize()[0:4])
        if (line.lower())[0:4] != ".end":
            modelInfo = line.split("*@")
            if len(modelInfo) == 2:
                netlist.append(modelInfo[0]+"\n")
                if  modelInfo[1][0] == '@':
                    netlist.append(".include " + modelInfo[1][1:])
                else:
                    if isNativeLTspiceModelLib(modelInfo[1].replace("\n", "")):
                        netlist.append(".lib " + modelInfo[1])
                    else:
                        netlist.append(".include " + modelInfo[1])
            else:
                #line = line.replace("@", "\n")
                netlist.append(line)
            #if DEBUG: print("Ajout de : " + line)
        # Recherche des composants paramètrables
        match = re.match(r".*\{(.*)\}.*", line)
        if match is not None:  
            if DEBUG: print("Parameter : " +  match.group(1))
            # Was it in the previous session ?
            isInPrevious = False
            for param in previousParameters:
                if param[0] == match.group(1):
                    parameters.append(param)
                    isInPrevious = True
                    if DEBUG: print("Append a param")
            if isInPrevious == False:
                parameters.append([match.group(1), "", "0", "", "", "", ""])


    fichierIn.close()
    for i in range(0,len(netlist)): netlist[i] = netlist[i].replace("\n", "")

if netlistExist:
    getNetlist()

def runSimulation(directive):
    saveConfig()

    if netlistExist == False:
        showinfo("Information","Command line doesn't specify a netlist file")
        return
    # Apply Monte Carlo and Worst Case
    replaceRLCvaluesInNetist()

    if DEBUG: print("Insertion de la directive : " + directive)
    #Nom du fichier de sortie à partir du nom du fichier d'entrée
    fichierCIRforLTspice = fichierCIR[:-4] + "LTspice.net"

    # Parameters directives
    paramDirective = ""
    for param in parameters:
        # One point analysis or step mode
        if param[2] == "0":
            paramDirective = "."
        else:
            paramDirective = ".step "

        # Octave or decade stepping mode
        if param[2] == "2":
            paramDirective += "oct "
        if param[2] == "3":
            paramDirective += "dec "

        # Key word for Temp or Other parameters
        if param[0] == "Global Temperature":
            paramDirective += "temp "
        else:
            paramDirective += "param " + param[0] + " "
        # Data format for parameter variation
        if param[2] == "0":
            paramDirective += param[1]
        if param[2] == "1":
            paramDirective += param[3] + " " + param[4] + " " + param[5]
        if param[2] == "2":
            paramDirective += param[3] + " " + param[4] + " " + param[5]
        if param[2] == "3":
            paramDirective += param[3] + " " + param[4] + " " + param[5]
        if param[2] == "4":
            paramDirective += "list " + param[6]
        if DEBUG: print(paramDirective)
        netlist.append(paramDirective)

    if standardLibVar.get() == 1:
        netlist.append(".lib standard.bjt")
        netlist.append(".lib standard.dio")
        netlist.append(".lib standard.mos")
        netlist.append(".lib standard.jft")
    # Add .tran, .ac or .dc directive
    netlist.append(directive)
    netlist.append(".end")

    # Create asc file for LTspice
    fichierCIRforLTspice = fichierCIR[:-4] + "LTspice.asc"
    fichierOut = open(fichierCIRforLTspice, 'w+')    
    fichierOut.write("Version 4\n")
    fichierOut.write("SHEET 1 1096 680\n")
    fichierOut.write("TEXT -56 32 Left 2 !")
    for line in netlist:
        fichierOut.write(line + "\\n")
    fichierOut.write("\n")
    fichierOut.flush()
    fichierOut.close()

    # Run LTspice with asc file
    if os.path.isfile(LTspiceExecInput.get()):
        os.execl(LTspiceExecInput.get(), "-ascii", fichierCIRforLTspice)
        #print("start cmd /k \"" + LTspiceExecInput.get() + " " + fichierCIRforLTspice + "\"")
        #os.system("start cmd /k \"C:\\Program Files\\LTC\\LTspiceXVII\\XVIIx64.exe " + fichierCIRforLTspice + "\"")
    else:
        showerror("Start LTspice Error", "Wrong LTspice executable file.\nSelect it in the configuration tab.")

def addInputWidget(frame, label, unite, largeur):
    unCadre = Frame(frame)
    Label(unCadre, text=label + " : ").pack(padx=5, pady=5, side=LEFT)
    unInput = Entry(unCadre, width=largeur)
    unInput.pack(padx=5, pady=5, side=LEFT)
    if unite != "":
        Label(unCadre, text=unite).pack(padx=5, pady=5, side=LEFT)
    unCadre.pack(fill=X)
    return unInput

#****************************************************************************
# Base
#****************************************************************************
def analysisTypeComboBoxUpdate(eventObject):
    if DEBUG: print("")
    if analysisTypeComboBox.current() == 0:
        AllTabs.hide(dcAnalysisTab)
        AllTabs.hide(acAnalysisTab)
        AllTabs.add(transientAnalysisTab)
        AllTabs.select(transientAnalysisTab)
        AllTabs.hide(opAnalysisTab)
    if analysisTypeComboBox.current() == 1:
        AllTabs.hide(transientAnalysisTab)
        AllTabs.hide(acAnalysisTab)
        AllTabs.hide(opAnalysisTab)
        AllTabs.add(dcAnalysisTab)
        AllTabs.select(dcAnalysisTab)
    if analysisTypeComboBox.current() == 2:
        AllTabs.hide(transientAnalysisTab)
        AllTabs.hide(dcAnalysisTab)
        AllTabs.hide(opAnalysisTab)
        AllTabs.add(acAnalysisTab)
        AllTabs.select(acAnalysisTab)
    if analysisTypeComboBox.current() == 3:
        AllTabs.hide(transientAnalysisTab)
        AllTabs.hide(dcAnalysisTab)
        AllTabs.hide(acAnalysisTab)
        AllTabs.add(opAnalysisTab)
        AllTabs.select(opAnalysisTab)

configAnalysisFrame = ttk.Frame(monAppli)
analysisTypeFrame = Frame(configAnalysisFrame)
analysisTypeChoices=["Transient Analysis", "DC Sweep Analysis", "AC Sweep Analysis", "Bias Point Analysis"]
analysisTypeComboBox = ttk.Combobox(analysisTypeFrame, values=analysisTypeChoices, state="readonly")
analysisTypeComboBox.current(0)
analysisTypeComboBox.pack(padx=5, pady=5)
analysisTypeFrame.pack(side=LEFT)
analysisTypeComboBox.bind("<<ComboboxSelected>>", analysisTypeComboBoxUpdate)
def startSimulationProcess():
    if analysisTypeComboBox.current() == 0: startTransientAnalysis()
    if analysisTypeComboBox.current() == 1: startDCAnalysis()
    if analysisTypeComboBox.current() == 2: startACAnalysis()
    if analysisTypeComboBox.current() == 3: startopAnalysis()

startSimulationProcessButton = Button(configAnalysisFrame, text="Run simulation", command=startSimulationProcess)
startSimulationProcessButton.pack(side=RIGHT)
configAnalysisFrame.pack(side=TOP, fill=X)

AllTabs = ttk.Notebook(monAppli)   # Création du système d'AllTabs
AllTabs.pack()

#****************************************************************************
# opAnalysisTab
#****************************************************************************
opAnalysisTab = ttk.Frame(AllTabs)       # Ajout de l'onglet 1
opAnalysisTab.pack()
AllTabs.add(opAnalysisTab, text=' Bias Point Analysis ')      # Nom de l'onglet 1
AllTabs.hide(opAnalysisTab)

def startopAnalysis():
    if DEBUG: print("Start simulation ...")
    # Create directive string
    directive = ".op"
    runSimulation(directive)

#****************************************************************************
# transientAnalysisTab : temporal analysis
#****************************************************************************
transientAnalysisTab = ttk.Frame(AllTabs)
transientAnalysisTab.pack()
AllTabs.add(transientAnalysisTab, text=' Transient Analysis ')
runToTimeCadre = Frame(transientAnalysisTab)
Label(runToTimeCadre, text="Run to time : ").pack(padx=5, pady=5, side=LEFT)
runToTimeInput = Entry(runToTimeCadre, width=10)
runToTimeInput.pack(padx=5, pady=5, side=LEFT)
Label(runToTimeCadre, text="s").pack(padx=5, pady=5, side=LEFT)
runToTimeCadre.pack(fill=X)

#transientAnalysisTab.config()

startSavingDataCadre = Frame(transientAnalysisTab)
Label(startSavingDataCadre, text="Start saving data after (default is 0) : ").pack(padx=5,pady=5, side=LEFT)
startSavingDataInput = Entry(startSavingDataCadre, width = 10)
startSavingDataInput.pack(padx=5, pady=5, side=LEFT)
Label(startSavingDataCadre, text="s").pack(padx=5, pady=5, side=LEFT)
startSavingDataCadre.pack(fill=X)

maxStepSizeInput = addInputWidget(transientAnalysisTab, "Step Size (default is 0)", "s", 10)
uicVar = IntVar()
uicVar.set(1)
uicCheckbutton = Checkbutton(transientAnalysisTab, text="Use Initial Conditions (.ic command; all is null otherwise)", variable = uicVar)
uicCheckbutton.pack(side=LEFT, anchor="n")

def setIfEmpty(objet, value):
    if objet.get() == "":
        objet.delete(0, END)
        objet.insert(0, value)

def startTransientAnalysis():
    if DEBUG: print("Start simulation ...")
    # Simulation step
    setIfEmpty(maxStepSizeInput, "1u")
    if DEBUG: print ("maxStepSize = " + maxStepSizeInput.get())
    # Simulation length
    setIfEmpty(runToTimeInput, "1")
    if DEBUG: print ("runToTime = " + runToTimeInput.get())
    setIfEmpty(startSavingDataInput, "0")
    if DEBUG: print ("startSavingData = " + startSavingDataInput.get())
    # Create directive string
    directive = ".tran " + maxStepSizeInput.get() + " " + runToTimeInput.get() + " " + startSavingDataInput.get()
    if uicVar.get() == 1: directive += " UIC"
    runSimulation(directive)

#****************************************************************************
# DC Sweep Analysis Tab
#****************************************************************************
dcAnalysisTab = ttk.Frame(AllTabs) 
dcAnalysisTab.pack(padx=5, pady=5)
AllTabs.add(dcAnalysisTab, text=' DC Sweep Analysis ')
AllTabs.hide(dcAnalysisTab)

# Source1
dcSrc1Frame = LabelFrame(dcAnalysisTab, text="DC Sweep Source 1", padx = 10, pady = 10)
dcSrc1Frame.pack(fill="both", expand="yes")

def src1ComboBoxUpdate(eventObject):
    if DEBUG: print("Selection : " + str(dcSweepType1ComboBox.current()))
    if dcSweepType1ComboBox.current() == 3:
        dcStartSrc1Input.config(state = 'disabled')
        dcEndSrc1Input.config(state = 'disabled')
        nbPtsSrc1Input.config(state = 'disabled')
        dcListSrc1Input.config(state = 'normal')
    else:
        dcStartSrc1Input.config(state = 'normal')
        dcEndSrc1Input.config(state = 'normal')
        nbPtsSrc1Input.config(state = 'normal')
        dcListSrc1Input.config(state = 'disabled')
      
dcNameSrc1Input = addInputWidget(dcSrc1Frame, "Source Name 1", "", 10)

dcSweepType1Frame = Frame(dcSrc1Frame)
dcSweepTypeChoices=["Linear", "Log octave","Log decade", "List"]
dcSweepType1ComboBox = ttk.Combobox(dcSweepType1Frame, width=12, values=dcSweepTypeChoices, state="readonly")
dcSweepType1ComboBox.current(0)
dcSweepType1ComboBox.pack(side=LEFT)
dcSweepType1Frame.pack(side=LEFT,anchor="n")
dcSweepType1ComboBox.bind("<<ComboboxSelected>>", src1ComboBoxUpdate)

dcStartSrc1Input = addInputWidget(dcSrc1Frame, "Start value", "", 10)
dcEndSrc1Input = addInputWidget(dcSrc1Frame,   "End value  ", "", 10)

nbPtsSrc1Cadre = Frame(dcSrc1Frame)
nbPtsSrc1Label = Label(nbPtsSrc1Cadre, text="Increment or Points/decade or Points/Oct : ")
nbPtsSrc1Label.pack(padx=5,pady=5, side=LEFT)
nbPtsSrc1Input = Entry(nbPtsSrc1Cadre, width = 10)
nbPtsSrc1Input.pack(padx=5, pady=5, side=LEFT)
nbPtsSrc1Cadre.pack(fill=X)

dcListSrc1Input = addInputWidget(dcSrc1Frame, "Value List", "", 120)
dcListSrc1Input.config(state = 'disabled')

# Source2
dcSrc2Frame = LabelFrame(dcAnalysisTab, text="DC Sweep Source 2", padx = 10, pady = 10)
dcSrc2Frame.pack(fill="both", expand="yes")

def src2ComboBoxUpdate(eventObject):
    if DEBUG: print("Selection : " + str(dcSweepType2ComboBox.current()))
    if dcSweepType2ComboBox.current() == 3:
        dcStartSrc2Input.config(state = 'disabled')
        dcEndSrc2Input.config(state = 'disabled')
        nbPtsSrc2Input.config(state = 'disabled')
        dcListSrc2Input.config(state = 'normal')
    else:
        dcStartSrc2Input.config(state = 'normal')
        dcEndSrc2Input.config(state = 'normal')
        nbPtsSrc2Input.config(state = 'normal')
        dcListSrc2Input.config(state = 'disabled')

        
dcNameSrc2Input = addInputWidget(dcSrc2Frame, "Source Name 2", "", 10)

dcSweepType2Frame = Frame(dcSrc2Frame)
dcSweepTypeChoices=["Linear", "Log octave","Log decade", "List"]
dcSweepType2ComboBox = ttk.Combobox(dcSweepType2Frame, width=12, values=dcSweepTypeChoices, state="readonly")
dcSweepType2ComboBox.current(0)
dcSweepType2ComboBox.pack(side=LEFT)
dcSweepType2Frame.pack(side=LEFT, anchor="n")
dcSweepType2ComboBox.bind("<<ComboboxSelected>>", src2ComboBoxUpdate)

dcStartSrc2Input = addInputWidget(dcSrc2Frame, "Start value", "", 10)
dcEndSrc2Input = addInputWidget(dcSrc2Frame,   "End value  ", "", 10)

nbPtsSrc2Cadre = Frame(dcSrc2Frame)
nbPtsSrc2Label = Label(nbPtsSrc2Cadre, text="Increment or Points/decade or Points/Oct : ")
nbPtsSrc2Label.pack(padx=5,pady=5, side=LEFT)
nbPtsSrc2Input = Entry(nbPtsSrc2Cadre, width = 10)
nbPtsSrc2Input.pack(padx=5, pady=5, side=LEFT)
nbPtsSrc2Cadre.pack(fill=X)

dcListSrc2Input = addInputWidget(dcSrc2Frame, "Value List", "", 120)
dcListSrc2Input.config(state = 'disabled')

def startDCAnalysis():
    if DEBUG: print("Run simulation ...")
    directive = ".dc "
    src1OK = True
    if dcNameSrc1Input.get() != "":
        directive += dcNameSrc1Input.get() + " "
        if dcSweepType1ComboBox.current() != 3:
            if dcStartSrc1Input.get() != "" and dcEndSrc1Input.get()!= "" and nbPtsSrc1Input.get() != "":
                if dcSweepType1ComboBox.current() == 1:
                    directive += "oct "
                if dcSweepType1ComboBox.current() == 2:
                    directive += "dec "
                directive += dcStartSrc1Input.get() + " " + dcEndSrc1Input.get() + " " + nbPtsSrc1Input.get()
            else:
                showerror("Incomplete parameters", "Write parameters and retry")
                src1OK = False  
        else:
            if dcListSrc1Input.get() != "":
                # List
                directive += "list " + dcListSrc1Input.get()
            else:
                showerror("Incomplete parameters", "Write parameters and retry")    
                src1OK = False  
    else:
        showerror("Incomplete parameters", "Retry with a source name")
        src1OK = False
    
    if src1OK:
        # Add second source
        if dcNameSrc2Input.get() != "":
            if dcSweepType2ComboBox.current() != 3:
                directive += " " + dcNameSrc2Input.get() + " "
                if dcStartSrc2Input.get() != "" and dcEndSrc2Input.get()!= "" and nbPtsSrc2Input.get() != "":
                    if dcSweepType2ComboBox.current() == 1:
                        directive += "oct "
                    if dcSweepType2ComboBox.current() == 2:
                        directive += "dec "
                    directive += dcStartSrc2Input.get() + " " + dcEndSrc2Input.get() + " " + nbPtsSrc2Input.get()
                else:
                    showerror("Incomplete parameters", "Write parameters and retry")
                    src1OK = False  
            else:
                if dcListSrc2Input.get() != "":
                    directive += " " + dcNameSrc2Input.get() + " "
                    # List
                    directive += "list " + dcListSrc2Input.get()
                else:
                    showerror("Incomplete parameters", "Write parameters and retry")    
                    src1OK = False  
    if src1OK:
        runSimulation(directive)

#****************************************************************************
# AC Sweep Analysis Tab
#****************************************************************************
acAnalysisTab = ttk.Frame(AllTabs) 
acAnalysisTab.pack()
AllTabs.add(acAnalysisTab, text=' AC Sweep Analysis ')
AllTabs.hide(acAnalysisTab)

acSweepFrame = LabelFrame(acAnalysisTab, text="AC Sweep Type", padx = 10, pady = 10)
acSweepFrame.pack(fill="both", expand="yes")

acSweepTypeFrame = Frame(acSweepFrame)
acSweepTypeChoices=["Linear", "Log octave","Log decade"]
acSweepTypeComboBox = ttk.Combobox(acSweepTypeFrame, values=acSweepTypeChoices, state="readonly")
acSweepTypeComboBox.current(0)
acSweepTypeComboBox.pack(side=LEFT)
acSweepTypeFrame.pack(side=TOP,anchor=W)

acStartFrequencyInput = addInputWidget(acSweepFrame, "Start frequency", "Hz", 10)
acEndFrequencyInput = addInputWidget(acSweepFrame,   "End frequency  ", "Hz", 10)

nbPtsCadre = Frame(acSweepFrame)
nbPtsLabel = Label(nbPtsCadre, text="Points or Points/decade or Points/Oct : ")
nbPtsLabel.pack(padx=5,pady=5, side=LEFT)
nbPtsInput = Entry(nbPtsCadre, width = 10)
nbPtsInput.pack(padx=5, pady=5, side=LEFT)
nbPtsCadre.pack(fill=X)

def startACAnalysis():
    if DEBUG: print("Run simulation ...")
    # Start frequency
    setIfEmpty(acStartFrequencyInput, "10")
    if DEBUG: print ("acStartFrequency = " + acStartFrequencyInput.get())
    # End frequency
    setIfEmpty(acEndFrequencyInput, "10Meg")
    if DEBUG: print ("acEndFrequency = " + acEndFrequencyInput.get())
    # Total points or points per decade or points per octave
    setIfEmpty(nbPtsInput, "100")
    if DEBUG: print ("nbPts = " + nbPtsInput.get())
    # Create directive string
    directive = ".ac "
    if acSweepTypeComboBox.current() == 0:
        directive = directive + "lin"
    if acSweepTypeComboBox.current() == 1:
        directive = directive + "oct"
    if acSweepTypeComboBox.current() == 2:
        directive = directive + "dec"
    directive = directive + " " + nbPtsInput.get()
    directive = directive + " " + acStartFrequencyInput.get()
    directive = directive + " " + acEndFrequencyInput.get()
    runSimulation(directive)

#****************************************************************************
# Parameters Tab
#****************************************************************************
parametersTab = ttk.Frame(AllTabs)
parametersTab.pack()
AllTabs.add(parametersTab, text=' Parameters ')

def loadInput(objet, value):
    objet.delete(0, END)
    objet.insert(0, value)

paramHeaderFrame = Frame(parametersTab)
Label(paramHeaderFrame, text="Parameter name : ").pack(side=TOP)

paramChoices=[]
# Get parameters name in parameters list
if DEBUG: print(parameters)
for param in parameters:
    paramChoices.append(param[0])

# Disabled Parameters tab if paramChoices is empty
if len(paramChoices) == 0:
    AllTabs.hide(parametersTab)

paramComboBox = ttk.Combobox(paramHeaderFrame, width=20, values=paramChoices, state="readonly")
paramComboBox.current(0)
paramComboBox.pack()
paramHeaderFrame.pack(side=TOP)

def loadParamInputs():
    index = paramComboBox.current()
    if DEBUG: print("Load parameters at index " + str(index))
    defaultValueParamInput.config(state = 'normal')
    loadInput(defaultValueParamInput, parameters[index][1])
    if DEBUG: print("Load list : " + defaultValueParamInput.get())
    if DEBUG: print("Load list : " + parameters[index][1])
    loadInput(startParamInput, parameters[index][3])
    loadInput(endParamInput, parameters[index][4])
    loadInput(nbPtsParamInput, parameters[index][5])
    loadInput(listParamInput, parameters[index][6])
    listParamInput.delete(0, END)
    listParamInput.insert(0, parameters[index][6])
    paramTypeComboBox.current(int(parameters[index][2]))

def paramComboBoxUpdate(eventObject):
    startParamInput.config(state = 'normal')
    endParamInput.config(state = 'normal')
    nbPtsParamInput.config(state = 'normal')
    listParamInput.config(state = 'normal')
    loadParamInputs()
    setParamInputsState()

def saveParamData():
    index = paramComboBox.current()
    if DEBUG: print("Save data at index = " + str(index))
    parameters[index][1] = defaultValueParamInput.get()
    parameters[index][2] = str(paramTypeComboBox.current())
    parameters[index][3] = startParamInput.get()
    parameters[index][4] = endParamInput.get()
    parameters[index][5] = nbPtsParamInput.get()
    parameters[index][6] = listParamInput.get()
    if DEBUG: print("Save list : " + listParamInput.get())
    if DEBUG: print("Save list : " + parameters[index][6])
    
def saveParamDataEvent(eventObject):
    saveParamData()
    
paramComboBox.bind("<<ComboboxSelected>>", paramComboBoxUpdate)
defaultValueParamInput = addInputWidget(paramHeaderFrame, "Default Value", "", 10)
defaultValueParamInput.bind("<KeyRelease>", saveParamDataEvent)

paramFrame = Frame(parametersTab)
paramTypeChoices=["Default value", "Linear", "Log octave","Log decade", "List"]
paramTypeComboBox = ttk.Combobox(paramFrame, width=18, values=paramTypeChoices, state="readonly")
paramTypeComboBox.current(0)
paramTypeComboBox.pack()
paramFrame.pack(side=LEFT,anchor="n")

# Parameter type (by increment or list)
def setParamInputsState():
    if paramTypeComboBox.current() == 0:
        defaultValueParamInput.config(state = 'normal')
        startParamInput.config(state = 'disabled')
        endParamInput.config(state = 'disabled')
        nbPtsParamInput.config(state = 'disabled')
        listParamInput.config(state = 'disabled')
    else: 
        defaultValueParamInput.config(state = 'disabled')
        if paramTypeComboBox.current() == 4:
            startParamInput.config(state = 'disabled')
            endParamInput.config(state = 'disabled')
            nbPtsParamInput.config(state = 'disabled')
            listParamInput.config(state = 'normal')
        else:
            startParamInput.config(state = 'normal')
            endParamInput.config(state = 'normal')
            nbPtsParamInput.config(state = 'normal')
            listParamInput.config(state = 'disabled')

def paramTypeComboBoxUpdate(eventObject):
    parameters[paramComboBox.current()][2] = str(paramTypeComboBox.current())
    setParamInputsState()

paramTypeComboBox.bind("<<ComboboxSelected>>", paramTypeComboBoxUpdate)

startParamInput = addInputWidget(paramFrame, "Start value", "", 10)
startParamInput.bind("<KeyRelease>", saveParamDataEvent)
endParamInput = addInputWidget(paramFrame,   "End value  ", "", 10)
endParamInput.bind("<KeyRelease>", saveParamDataEvent)

nbPtsParamFrame = Frame(paramFrame)
nbPtsParamLabel = Label(nbPtsParamFrame, text="Increment or Points/decade or Points/Oct : ")
nbPtsParamLabel.pack(padx=5,pady=5, side=LEFT)
nbPtsParamInput = Entry(nbPtsParamFrame, width = 10)
nbPtsParamInput.pack(padx=5, pady=5, side=LEFT)
nbPtsParamFrame.pack(fill=X)
nbPtsParamInput.bind("<KeyRelease>", saveParamDataEvent)

listParamInput = addInputWidget(parametersTab, "Value List", "", 120)
listParamInput.config(state = 'disabled')
listParamInput.bind("<KeyRelease>", saveParamDataEvent)

loadParamInputs()
setParamInputsState()

#****************************************************************************
# mcWc Tab (Monte Carlo and Worst Case Analysis)
#****************************************************************************
mcWcTab = ttk.Frame(AllTabs)
mcWcTab.pack()
AllTabs.add(mcWcTab, text=' Monte Carlo/Worst Case ')

mcWcTypeFrame = Frame(mcWcTab)
mcWcTypeChoices=["No MC or Worst Case Analysis", "Monte Carlo", "Worst Case"]
mcWcTypeComboBox = ttk.Combobox(mcWcTypeFrame, values=mcWcTypeChoices, state="readonly", width=30)
mcWcTypeComboBox.current(0)
mcWcTypeComboBox.pack(side=LEFT)
mcWcTypeFrame.pack(side=TOP,anchor=W, padx=5, pady=5)

# Monte Carlo and Worst Case work only for Resistor, Capacitor and Inductor
def replaceRLCvaluesInNetist():
    global netlist
    newNetlist = []
    nbWC = 0
    for lineCounter in range(0, len(netlist)):
        line = netlist[lineCounter]
        if len(line) > 0:
            if line[0] == "R" or line[0] == "L" or line[0] == "C":
                # tolerance ?
                parts = line.split(" ")
                if len(parts) > 4:
                    if DEBUG: print(parts[4][0:4].lower())
                    if parts[4][0:4].lower() == "tol=" and len(parts[4]) > 4:
                        if DEBUG: print("Tolérance pour " + str(parts[0]))
                        # Extract tolerance
                        tolerance = parts[4].split("=")[1]
                        if tolerance[-1] == "%":
                            tolerance = tolerance[0:-1]
                            tolerance = str(int(tolerance)/100)
                            if DEBUG: print("Tolerance : " + str(tolerance))
                        if mcWcTypeComboBox.current() != 0:
                            # MC parameters
                            # Change value
                            value = parts[3]
                            if mcWcTypeComboBox.current() == 1:
                                parts[3] = "{gauss3(" + value + "," + tolerance + ")}"
                            else:
                                parts[3] = "{wc(" + value + "," + tolerance + "," + str(nbWC) +")}"
                                nbWC = nbWC + 1
                            line = parts[0] + " " + parts[1] + " " + parts[2] + " " + parts[3]
                            if len(parts) > 5:
                                i = 5
                                while i <= len(parts)-1:
                                    line += " " + parts[i]
                                    i = i + 1
                        else:
                            parts[4] = ""
                            i = 1
                            line = parts[0]
                            while i <= len(parts)-1:
                                line += " " + parts[i]
                                i = i + 1

            if DEBUG: print(line)    
        netlist[lineCounter] = line
    if mcWcTypeComboBox.current() == 1:
        netlist.append(".func gauss3(value,tol) value*(1+gauss(tol/3))")
        if mcRunsSlider.get() == 1:
            netlist.append(".param run=1")
        else:
            netlist.append(".step param run 1 " + str(mcRunsSlider.get()) + " 1")
        
    if mcWcTypeComboBox.current() == 2:
        netlist.append(".func wc(nom,tol,index) if(run==numruns,nom,if(binary(run,index),nom*(1+tol),nom*(1-tol)))")
        netlist.append(".func binary(run,index) floor(run/(2**index))-2*floor(run/(2**(index+1)))")
        netlist.append(".param numruns=" + str(2**nbWC))
        netlist.append(".step param run 1 " + str(2**nbWC) + " 1")

    if DEBUG: print("New netlist : ")
    if DEBUG: print(netlist)

def mcWcTypeComboBoxUpdate(eventObject):
    if mcWcTypeComboBox.current() != 1:
        mcRunsSlider.config(state="disabled")
    else:
        mcRunsSlider.config(state="normal")

mcWcTypeComboBox.bind("<<ComboboxSelected>>", mcWcTypeComboBoxUpdate)

mcWcParamFrame = Frame(mcWcTab)
Label(mcWcParamFrame, text="Number of runs :").pack(padx=5, pady=5,side=LEFT)
mcRuns = IntVar()
mcRunsSlider = Scale(mcWcParamFrame, from_=1, to=100, orient=HORIZONTAL, length=500, state="disabled")#,command=mcRunsUpdate)
mcRunsSlider.pack(side=RIGHT)
mcWcParamFrame.pack()
wcDevicesList=[""]

# Peek R, L, C components with tolerances in netlist file : now done in simulation function
#replaceRLCvaluesInNetist()

#****************************************************************************
# exportLibTab Tab
#****************************************************************************
exportLibTab = ttk.Frame(AllTabs)
exportLibTab.pack()
AllTabs.add(exportLibTab, text=' Library manager ')

exportLibFrame = LabelFrame(exportLibTab, text="Export Standard Library to Kicad", padx = 10, pady = 10)
exportLibFrame.pack(fill=X)

exportLibComboFrame = Frame(exportLibFrame)
exportLibChoices=["Inductors", "Beads", "Capacitors"]
exportLibComboBox = ttk.Combobox(exportLibComboFrame, values=exportLibChoices, state="readonly")
exportLibComboBox.current(0)
exportLibComboBox.pack(side=LEFT)
exportLibComboFrame.pack(padx=5, pady=5)

def startExportLib():
    if exportLibComboBox.current() == 0:
        # Export Inductors
        if DEBUG: print("Export inductors library to KiCad")
        fileIn = open("./libTxt/standard.ind.txt", 'r', encoding='utf-8')
        inductors = fileIn.readlines()
        fileIn.close
        fileIn = open("./libTxt/inductor.template", 'r', encoding='utf-8')
        template = fileIn.readlines()
        fileIn.close

        # Write Kicad Inductors lib file
        fileOut = open("./libForKicad/LTspiceInductors.lib", 'w+', encoding='utf-8')
        # File Header
        fileOut.write("EESchema-LIBRARY Version 2.4\n")
        fileOut.write("#encoding utf-8\n")
        fileOut.write("#\n")
        # Write KiCad Inductors documentation file
        fileOutDoc = open("./libForKicad/LTspiceInductors.dcm", 'w+', encoding='utf-8')
        # File Header
        fileOutDoc.write("EESchema-DOCLIB  Version 2.0\n")

        for component in inductors:
            # Build spice line
            details = component.split("\t")
            if len(details) == 7:
                # Suppression des espaces dans les lines de details
                details[2] = details[2].replace(" ", "_")
                for i in [0, 3, 4, 5, 6]:
                    details[i] = details[i].replace(" ", "")
                details[6] = details[6].strip("\n")
                for line in template:
                    for i in range(0,7):
                        #if DEBUG: print("%i% = " + "%" + str(i) + "%")
                        line = line.replace("%" + str(i) + "%", details[i])
                    fileOut.write(line)
                # Documentation
                fileOutDoc.write("$CMP " + details[2] + "\n")
                fileOutDoc.write("D " + details[1] + " " + details[0] + "µ Ipk=" + details[3] + "A Rser=" + details[4] + "Ohm Rpar=" + details[5] + "Ohm Cpar=" + details[6] + "pF\n")
                fileOutDoc.write("$ENDCMP\n")
        fileOut.write("#\n")
        fileOut.write("#End Library\n")
        fileOut.close
        fileOutDoc.write("#End Doc Library\n")
        fileOutDoc.close
    if exportLibComboBox.current() == 1:
        # Export Inductors
        if DEBUG: print("Export inductors library to KiCad")
        fileIn = open("./libTxt/standard.bead.txt", 'r', encoding='utf-8')
        inductors = fileIn.readlines()
        fileIn.close
        fileIn = open("./libTxt/inductor.template", 'r', encoding='utf-8')
        template = fileIn.readlines()
        fileIn.close

        # Write Kicad Beads lib file
        fileOut = open("./libForKicad/LTspiceBeads.lib", 'w+', encoding='utf-8')
        # File Header
        fileOut.write("EESchema-LIBRARY Version 2.4\n")
        fileOut.write("#encoding utf-8\n")
        fileOut.write("#\n")
        # Write KiCad Inductors documentation file
        fileOutDoc = open("./libForKicad/LTspiceBeads.dcm", 'w+', encoding='utf-8')
        # File Header
        fileOutDoc.write("EESchema-DOCLIB  Version 2.0\n")

        for component in inductors:
            # Build spice line
            spiceline = ""
            details = component.split("\t")
            if len(details) == 7:
                # Suppression des espaces dans les lines de details
                details[2] = details[2].replace(" ", "_")
                for i in [0, 3, 4, 5, 6]:
                    details[i] = details[i].replace(" ", "")
                details[6] = details[6].strip("\n")
                for line in template:
                    for i in range(0,7):
                        #if DEBUG: print("%i% = " + "%" + str(i) + "%")
                        line = line.replace("%" + str(i) + "%", details[i])
                    fileOut.write(line)
                # Documentation
                fileOutDoc.write("$CMP " + details[2] + "\n")
                fileOutDoc.write("D " + details[1] + " " + details[0] + "µ Ipk=" + details[3] + "A Rser=" + details[4] + "Ohm Rpar=" + details[5] + "Ohm Cpar=" + details[6] + "pF\n")
                fileOutDoc.write("$ENDCMP\n")
        fileOut.write("#\n")
        fileOut.write("#End Library\n")
        fileOut.close
        fileOutDoc.write("#End Doc Library\n")
        fileOutDoc.close

    if exportLibComboBox.current() == 2:
        # Export Capacitors
        if DEBUG: print("Export capacitors library to KiCad")
        fileIn = open("./libTxt/standard.cap.txt", 'r', encoding='utf-8')
        capacitors = fileIn.readlines()
        fileIn.close
        fileIn = open("./libTxt/capacitorPol.template", 'r', encoding='utf-8')
        capacitorPolTemplate = fileIn.readlines()
        fileIn.close
        fileIn = open("./libTxt/capacitor.template", 'r', encoding='utf-8')
        capacitorTemplate = fileIn.readlines()
        fileIn.close

        # Write Kicad Beads lib file
        fileOut = open("./libForKicad/LTspiceCapacitors.lib", 'w+', encoding='utf-8')
        # File Header
        fileOut.write("EESchema-LIBRARY Version 2.4\n")
        fileOut.write("#encoding utf-8\n")
        fileOut.write("#\n")
        # Write KiCad Inductors documentation file
        fileOutDoc = open("./libForKicad/LTspiceCapacitors.dcm", 'w+', encoding='utf-8')
        # File Header
        fileOutDoc.write("EESchema-DOCLIB  Version 2.0\n")

        for component in capacitors:
            # Build spice line
            spiceline = ""
            details = component.split("\t")
            if len(details) == 8:
                # Suppression des espaces dans les lines de details
                details[2] = details[2].replace(" ", "_")
                for i in [0, 4, 5, 6, 7]:
                    details[i] = details[i].replace(" ", "")
                details[7] = details[7].strip("\n")
                # Capacitor type
                if details[3] == "Tantalum" or details[3]=="Al electrolytic":
                    template = capacitorPolTemplate
                else:
                    template = capacitorTemplate 
                for line in template:
                    for i in range(0,8):
                        #if DEBUG: print("%i% = " + "%" + str(i) + "%")
                        line = line.replace("%" + str(i) + "%", details[i])
                    fileOut.write(line)
                # Documentation
                fileOutDoc.write("$CMP " + details[2] + "\n")
                fileOutDoc.write("D " + details[1] + " " + details[0] + "µ " + details[3] + " V=" + details[4] + "v Irms=" + details[5] + "A Rser=" + details[6] + "Ohm Lser=" + details[7] + "nH\n")
                fileOutDoc.write("$ENDCMP\n")
        fileOut.write("#\n")
        fileOut.write("#End Library\n")
        fileOut.close
        fileOutDoc.write("#End Doc Library\n")
        fileOutDoc.close

# Bouton de lancement de l'exportation   
startExportButton = Button(exportLibFrame, text="Export library", command=startExportLib)
startExportButton.pack(side = BOTTOM)

opAmpList = ["User entry or choose an OpAmp in LTspice Library"]
# CompleteList : fileName, componentName, modelName, libName, description 
opAmpCompleteList = [["", "", "", "", ""]]
# Get OpAmps from LTspice libraries
dir = os.listdir(LTspiceDocPath + "lib/sym/Opamps/")
for component in dir:
    fileIn = open(LTspiceDocPath + "lib/sym/Opamps/" + component)
    lines = fileIn.readlines()
    fileIn.close()
    componentName = component[:-4]
    modelName = ""
    libName = ""
    description = ""
    for line in lines:
        if len(line) > 7:
            if line[:7]== "SYMATTR":
                sl = line.split("SYMATTR ")
                if len(sl) == 2:
                    sl = sl[1]
                    s = sl.split("Value ")
                    if len(s) == 2:
                        componentName = s[1]
                    s = sl.split("Value2 ")
                    if len(s) == 2:
                        modelName = s[1]
                    s = sl.split("SpiceModel ")
                    if len(s) == 2:
                        libName = s[1]
                    s = line.split("Description ")
                    if len(s) == 2:
                        description = s[1]
    # Combobox add
    description = description.replace("\n", "")
    componentName = componentName.replace("\n", "")
    modelName = modelName.replace("\n", "")
    libName = libName.replace("\n", "")

    opAmpList.append(componentName + " " + description)
    opAmpCompleteList.append([component, componentName, modelName, libName, description])

def opAmpListComboBoxUpdate(eventObject):
    e = opAmpCompleteList[opAmpListComboBox.current()]
    symbolNameInput.delete(0, END)
    symbolNameInput.insert(0, e[1])
    symbolModelInput.delete(0, END)
    symbolModelInput.insert(0, e[2])
    symbolLibInput.delete(0,END)
    symbolLibInput.insert(0, e[3])

opAmpForPCBFrame = LabelFrame(exportLibTab, text="LTspice Op Amp Symbol For PCB compatibility", padx = 10, pady = 10)
opAmpListComboBox = ttk.Combobox(opAmpForPCBFrame, values=opAmpList, state="readonly", width=80)
opAmpListComboBox.current(0)
opAmpListComboBox.pack(side=TOP)
opAmpListComboBox.bind("<<ComboboxSelected>>", opAmpListComboBoxUpdate)

symbolNameInput = addInputWidget(opAmpForPCBFrame,"OpAmp name","", 15)
symbolModelInput = addInputWidget(opAmpForPCBFrame,"Model name","", 25)
symbolLibInput = addInputWidget(opAmpForPCBFrame, "Library (location of the model)","", 80)
symbolSDQ = ["5 Pins Simple OpAmp", "8 Pins Simple OpAmp", "8 Pins Dual OpAmp with single model", "14 Pins Quad OpAmp with single model", "8 Pins Dual OpAmp (model already writes for Dual OpAmp)", "14 Pins Quad OpAmp (model already writes for quad OpAmp)"]
symbolSDQComboBox = ttk.Combobox(opAmpForPCBFrame, width = 55, values=symbolSDQ, state="readonly")
symbolSDQComboBox.current(1)
symbolSDQComboBox.pack(anchor = "w")

opAmpForPCBFrame.pack(fill=X)

convertSymbolToKiCadFrame = LabelFrame(exportLibTab, text="Convert LTspice Symbol to KiCad", padx = 10, pady = 10)

def fileOrDirComboBoxUpdate(eventObject):
    print("File or Dir")
    if fileOrDirComboBox.current() == 0:
        symbolSrcLabel.config(text = "LTspice Symbol Source File : ")
    else:
        symbolSrcLabel.config(text = "LTspice Symbol Source Directory : ")

fileOrDirChoices = ["Convert a single LTspice Symbol File", "Convert a whole directory"]
fileOrDirComboBox = ttk.Combobox(convertSymbolToKiCadFrame, width = 70, values=fileOrDirChoices, state="readonly")
fileOrDirComboBox.current(0)
fileOrDirComboBox.pack()
fileOrDirComboBox.bind("<<ComboboxSelected>>", fileOrDirComboBoxUpdate)

symbolSrcFrame = Frame(convertSymbolToKiCadFrame)
symbolSrcLabel = Label(symbolSrcFrame, text="LTspice Symbol Source File : ")
symbolSrcLabel.pack(padx=5,pady=5, side=LEFT)
symbolSrcInput = Entry(symbolSrcFrame, width = 120)
symbolSrcInput.pack(padx=5, pady=5, side=LEFT)
symbolSrcFrame.pack()

kicadLibDestFrame = Frame(convertSymbolToKiCadFrame)
Label(kicadLibDestFrame, text="KiCad Library Destination File : ").pack(padx=5,pady=5, side=LEFT)
kicadLibDestInput = Entry(kicadLibDestFrame, width = 120)
kicadLibDestInput.pack(padx=5, pady=5, side=LEFT)
kicadLibDestFrame.pack()
convertSymbolToKiCadFrame.pack(fill=X)

def getSymbolSrcFile():
    if DEBUG: print("Dialog FileName or DirName")
    if fileOrDirComboBox.current() == 0:
        filename = filedialog.askopenfilename(initialdir="",
            title="Select Symbol Source File",
            filetypes = (("LTspice Symbol","*.asy"),("all files","*.*")))
    else:
        filename = filedialog.askdirectory(initialdir="",
        title="Select Symbols Source Directory")

    if filename != "":
        symbolSrcInput.delete(0, END)
        symbolSrcInput.insert(0, filename)    

symbolSrcButton = Button(symbolSrcFrame, text="Browse...", command=getSymbolSrcFile)
symbolSrcButton.pack(side = LEFT, fill=X)

def getKicadLibDestFile():
    if DEBUG: print("Dialog FileName")
    filename = filedialog.askopenfilename(initialdir="",
        title="Select Kicad Symbol Library Destination File",
        filetypes = (("KiCad Symbol Library","*.lib"),("all files","*.*")))
    if filename != "":
        kicadLibDestInput.delete(0, END)
        kicadLibDestInput.insert(0, filename)    

kicadLibDestButton = Button(kicadLibDestFrame, text="Browse...", command=getKicadLibDestFile)
kicadLibDestButton.pack(side = LEFT, fill=X)
def proceedConversion():
    print("Conversion of " + symbolSrcInput.get() + " to " + kicadLibDestInput.get())
    #convertToKicad(srcDir, srcFile, defaultDestDir, destLibrary, XUViewPin, scale)
    src = symbolSrcInput.get()
    dir = os.path.dirname(src)
    file =  os.path.basename(src)
    if fileOrDirComboBox.current() == 1:
        dir = dir + "/" + file
        file = ""
    lib_LTspice2Kicad.convertToKicad(dir, file, appDir + "/libForKiCad/", kicadLibDestInput.get(), "Y", 1.0)

convertSymbolToKiCadButton = Button(convertSymbolToKiCadFrame, text="Proceed conversion", command=proceedConversion)
convertSymbolToKiCadButton.pack()

def isSymbolAlreadyInLibrary(libraryName, symbolName):
    result = False
    fileOut = open(libraryName, 'r', encoding='utf-8')
    library = fileOut.readlines()
    fileOut.close()
    # Symbol already in library ?
    firstLineOfComponent = 2
    deleteComponent = False
    i = 0
    while i < len(library):
        if library[i].find("ENDDEF") != -1:
            firstLineOfComponent = i + 1
                # Replace symbol => Delete
            if DEBUG: print("Replace symbol.")
            else:
                if DEBUG: print("Existing symbol.")
                result = True
        i = i + 1
    fileOut = open("./libForKicad/LTspiceOpAmpsPCB.lib", 'w+', encoding='utf-8')
    for line in library:
        if line != "#End Library\n": fileOut.write(line)
    fileOut.flush()
    fileOut.close()
def createSymbolLib():
    if DEBUG: print("Create Symbol Lib of " + symbolNameInput.get())
    templateFileName = "SimpleOpAmp_5pins.template"
    componentSuffix = "_5pins"
    if symbolSDQComboBox.current() == 1:
        templateFileName = "SimpleOpAmp_8pins.template"
        componentSuffix = "_8pins_1opAmp"
    if symbolSDQComboBox.current() == 2:
        templateFileName = "DualOpAmp_8pins.template"
        componentSuffix = "_8pins_2opAmps"
    if symbolSDQComboBox.current() == 3:
        templateFileName = "QuadOpAmp_14pins.template"
        componentSuffix = "_14pins_4opAmps"
    if symbolSDQComboBox.current() == 4:
        templateFileName = "DualOpAmp_8pins.template"
        componentSuffix = "_8pins_2opAmps"
    if symbolSDQComboBox.current() == 5:
        templateFileName = "QuadOpAmp_14pins.template"
        componentSuffix = "_14pins_4opAmps"
    #e = opAmpCompleteList[opAmpListComboBox.current()]
    modelBaseInfo = symbolModelInput.get() + "*@" + symbolLibInput.get()
    modelBaseInfo = modelBaseInfo.split("*@")
    modelBaseInfo[0] = modelBaseInfo[0].strip(" ")
    if symbolModelInput.get() == "" or symbolNameInput.get() == "" or len(modelBaseInfo) != 2:
        showerror("Incomplete parameters", "Write parameters and retry...")
    else:
        # Import current library
        fileOut = open("./libForKicad/LTspiceOpAmpsPCB.lib", 'r', encoding='utf-8')
        library = fileOut.readlines()
        fileOut.close()
        for line in library:
            if line.find("DEF " + symbolNameInput.get() + componentSuffix + " ") != -1:
                showerror("Error", "Symbol is already in library.\nRun KiCad Symbol Editor and delete this component and try conversion again.")
                # Stop symbol creation
                return
        fileOut = open("./libForKicad/LTspiceOpAmpsPCB.lib", 'w+', encoding='utf-8')
        for line in library:
            if line != "#End Library\n": fileOut.write(line)
        fileOut.flush()
        fileOut.close()
        # Read template file
        templateFile = open("./libForKicad/" + templateFileName, 'r', encoding='utf-8')
        template = templateFile.readlines()
        templateFile.close()
        #Write symbol
        fileOut = open("./libForKicad/LTspiceOpAmpsPCB.lib", 'a', encoding='utf-8')
        for line in template:
            line = line.replace("%1%", symbolNameInput.get() + componentSuffix)
            line = line.replace("%2%", symbolNameInput.get() + componentSuffix)
            if symbolSDQComboBox.current() == 0 or symbolSDQComboBox.current() == 1 or symbolSDQComboBox.current() == 4 or symbolSDQComboBox.current() == 5:
                line = line.replace("%3%", symbolModelInput.get() + "*@" + symbolLibInput.get())
            else: 
                line = line.replace("%3%", symbolNameInput.get()+ componentSuffix + "*@MultiPartOpAmps.lib")
            fileOut.write(line)
            fileOut.flush()
        fileOut.close()      
        # Write model only for multiparts symbol
        if symbolSDQComboBox.current() == 2 or symbolSDQComboBox.current() == 3:
            fileOut = open("./libForKicad/ModelsForKicad/MultiPartOpAmps.lib", 'a', encoding="utf-8")
            fileOut.write("* Multipart model for " + symbolNameInput.get() + ". Based on model " + modelBaseInfo[0] + " located in " + modelBaseInfo[1] + "\n")
            fileOut.write(".subckt " + symbolNameInput.get() + componentSuffix)
            #fileOut.write(".subckt " + symbolNameInput.get() + componentSuffix)

            if symbolSDQComboBox.current() == 2:
                fileOut.write(" out1 in1- in1+ vcc- in2+ in2- out2 vcc+\n")
            if symbolSDQComboBox.current() == 3:
                fileOut.write(" out1 in1- in1+ vcc+ in2+ in2- out2 out3 in3- in3+ vcc- in4+ in4- out4\n")
            if isNativeLTspiceModelLib(modelBaseInfo[1].replace("\n", "")):
                fileOut.write(".lib " + modelBaseInfo[1] + "\n")
            else:
                fileOut.write(".include " + modelBaseInfo[1] + "\n")

            fileOut.write("XA in1+ in1- vcc+ vcc- out1 " + modelBaseInfo[0] + "\n")
            fileOut.write("XB in2+ in2- vcc+ vcc- out2 " + modelBaseInfo[0] + "\n")
            if symbolSDQComboBox.current() == 3:
                fileOut.write("XC in3+ in3- vcc+ vcc- out3 " + modelBaseInfo[0] + "\n")
                fileOut.write("XD in4+ in4- vcc+ vcc- out4 " + modelBaseInfo[0] + "\n")
            fileOut.write(".ends\n")
            fileOut.flush()
            fileOut.close()
opAmpForPCBButton = Button(opAmpForPCBFrame, text="Create Symbol", command=createSymbolLib)
opAmpForPCBButton.pack()

#* Multipart model for %1%. Based on model %2% located in %3% 
#.subckt %1% 1out 1in- 1in+ vcc- 2in+ 2in- 2out vcc+
#%3%
#XA 1in+ 1in- vcc+ vcc- 1out %2%
#XB 2in+ 2in- vcc+ vcc- 2out %2%
#.ends

#****************************************************************************
# Objets de l'onglet configTab : configuration
#****************************************************************************
configTab = ttk.Frame(AllTabs)       # Ajout de l'onglet configTab
configTab.pack()
AllTabs.add(configTab, text=' Configuration ')

LTspiceExecFrame = Frame(configTab)
Label(LTspiceExecFrame, text="LTspice executable file : ").pack(padx=5,pady=5, side=LEFT)
LTspiceExecInput = Entry(LTspiceExecFrame, width = 120)
LTspiceExecInput.pack(padx=5, pady=5, side=LEFT)
LTspiceLibDirFrame = Frame(configTab)
Label(LTspiceLibDirFrame, text="LTspice libraries directory : ").pack(padx=5,pady=5, side=LEFT)
LTspiceLibDirInput = Entry(LTspiceLibDirFrame, width = 120)
LTspiceLibDirInput.pack(padx=5, pady=5, side=LEFT)

def getExecFile():
    if DEBUG: print("Dialog FileName")
    filename = filedialog.askopenfilename(initialdir="",
        title="Select LTspice executable file",
        filetypes = (("Executable files","*.exe"),("all files","*.*")))
    if filename != "":
        LTspiceExecInput.delete(0, END)
        LTspiceExecInput.insert(0, filename)

def getLibDirectory():
    if DEBUG: print("Dialog dirName")    
    dirname = filedialog.askdirectory(initialdir="",
        title="Select LTspice libraries directory")
    if dirname != "":
        LTspiceLibDirInput.delete(0, END)
        LTspiceLibDirInput.insert(0, dirname)

getExecFileButton = Button(LTspiceExecFrame, text="Browse...", command=getExecFile)
getExecFileButton.pack(side = LEFT, fill=X)
LTspiceExecFrame.pack(fill=X)

getLibDirButton = Button(LTspiceLibDirFrame, text="Browse...", command=getLibDirectory)
getLibDirButton.pack(side = LEFT, fill=X)
LTspiceLibDirFrame.pack(fill=X)

standardLibFrame = Frame(configTab)
standardLibVar = IntVar()
standardLibVar.set(1)
standardLib = Checkbutton(standardLibFrame, text="Add LTspice standard library", variable = standardLibVar)
standardLib.pack(side=LEFT)
standardLibFrame.pack(fill=X)

#****************************************************************************
# About Tab definition
#****************************************************************************
aboutTab = ttk.Frame(AllTabs)
aboutTab.pack()
AllTabs.add(aboutTab, text=' About ')

about = "This program has been written to provide a simple bridge from KiCad to LTspice.\n"
about += "Eric PERONNIN\neric.peronnin@univ-nantes.fr"
aboutText = Text(aboutTab)
aboutText.pack(fill=X, padx = 10, pady = 10)
aboutText.insert('0.0', about)


defaultGeneralConfig = '{"LTspiceExec" : "C:/",'
defaultGeneralConfig += '"LTspiceLibDir" : "C:/"}'

defaultDataConfig = '{"nbPts" : "100", "acStartFrequency" : "10", "acEndFrequency" : "10Meg", '
defaultDataConfig += '"startSavingData" : "0",'
defaultDataConfig += '"runToTime" : "10m",'
defaultDataConfig += '"standardLib" : 1,'
defaultDataConfig += '"acSweepType" : 0,'
defaultDataConfig += '"maxStepSize" : "1u",'
defaultDataConfig += '"uicMode" : 1,'

defaultDataConfig += '"dcSweepType1" : 0,'
defaultDataConfig += '"dcNameSrc1" : "",'
defaultDataConfig += '"dcStartSrc1" : "",'
defaultDataConfig += '"dcEndSrc1" : "",'
defaultDataConfig += '"nbPtsSrc1" : "",'
defaultDataConfig += '"dcListSrc1" : "",'

defaultDataConfig += '"dcSweepType2" : 0,'
defaultDataConfig += '"dcNameSrc2" : "",'
defaultDataConfig += '"dcStartSrc2" : "",'
defaultDataConfig += '"dcEndSrc2" : "",'
defaultDataConfig += '"nbPtsSrc2" : "",'
defaultDataConfig += '"dcListSrc2" : ""'

defaultDataConfig += '}'

def saveConfig():
    if DEBUG: print("Save configuration...")

    # General config
    generalConfig = "{"
    generalConfig +=  '"LTspiceExec" : "' + str(LTspiceExecInput.get()) + '",'
    generalConfig +=  '"LTspiceLibDir" : "' + str(LTspiceLibDirInput.get()) + '"}'
    generalConfig = json.loads(generalConfig)
    with open('./generalConfig.json', 'w+') as f:
        json.dump(generalConfig, f)
        f.close()
    # Parameters
    if netlistExist == False: return
    with open(CIRprojectDirectory + '/parameters.txt', 'w+') as f:    
        for param in parameters:
            f.write(param[0])
            for i in range(1,7):
                f.write("," + param[i])
            f.write("\n")
        f.close()

    #dataconfig    
    dataConfig = "{"
    dataConfig +=  '"acStartFrequency" : "' + str(acStartFrequencyInput.get()) + '", '
    dataConfig +=  '"acEndFrequency" : "' + str(acEndFrequencyInput.get()) + '", '
    dataConfig +=  '"nbPts" : "' + str(nbPtsInput.get()) + '", '
    dataConfig +=  '"acSweepType" : ' + str(acSweepTypeComboBox.current()) + ', '

    dataConfig +=  '"standardLib" : ' + str(standardLibVar.get()) + ', '

    dataConfig +=  '"startSavingData" : "' + str(startSavingDataInput.get()) + '", '
    dataConfig +=  '"runToTime" : "' + str(runToTimeInput.get()) + '", '
    dataConfig +=  '"maxStepSize" : "' + str(maxStepSizeInput.get()) + '",'
    dataConfig +=  '"uicMode" : "' + str(uicVar.get()) + '",'

    dataConfig +=  '"dcSweepType1" : "' + str(dcSweepType1ComboBox.current()) + '",'
    dataConfig +=  '"dcNameSrc1" : "' + str(dcNameSrc1Input.get()) + '",'
    dataConfig +=  '"dcStartSrc1" : "' + str(dcStartSrc1Input.get()) + '",'
    dataConfig +=  '"dcEndSrc1" : "' + str(dcEndSrc1Input.get()) + '",'
    dataConfig +=  '"nbPtsSrc1" : "' + str(nbPtsSrc1Input.get()) + '",'
    dataConfig +=  '"dcListSrc1" : "' + str(dcListSrc1Input.get()) + '",'

    dataConfig +=  '"dcSweepType2" : "' + str(dcSweepType2ComboBox.current()) + '",'
    dataConfig +=  '"dcNameSrc2" : "' + str(dcNameSrc2Input.get()) + '",'
    dataConfig +=  '"dcStartSrc2" : "' + str(dcStartSrc2Input.get()) + '",'
    dataConfig +=  '"dcEndSrc2" : "' + str(dcEndSrc2Input.get()) + '",'
    dataConfig +=  '"nbPtsSrc2" : "' + str(nbPtsSrc2Input.get()) + '",'
    dataConfig +=  '"dcListSrc2" : "' + str(dcListSrc2Input.get()) + '"'
    dataConfig +=  '}'

    dataConfig = json.loads(dataConfig)
    with open(CIRprojectDirectory + '/dataConfig.json', 'w+') as f:
        json.dump(dataConfig, f)
        f.close()

saveConfigButton = Button(configTab, text="Save config", command=saveConfig)
saveConfigButton.pack(side = BOTTOM, fill=X)

def loadConfig():
    # General config
    if os.path.isfile(appDir + 'generalConfig.json'):
        with open(appDir + 'generalConfig.json', 'r') as f:
            generalConfig = json.load(f)
            f.close()
    else:
        if DEBUG: print("General Config file not found.")
        generalConfig = json.loads(defaultGeneralConfig)
        with open(appDir + 'generalConfig.json', 'w+') as f:
            json.dump(generalConfig, f)
            f.close()
    try:
        loadInput(LTspiceExecInput, generalConfig['LTspiceExec'])
        loadInput(LTspiceLibDirInput, generalConfig['LTspiceLibDir'])
    except KeyError:
        os.remove(appDir + 'generalConfig.json')
        return False

    # Stop at this point if program is running without CIR project    
    if netlistExist == False: return True

    # Data config file
    try:
        with open(CIRprojectDirectory + '/dataConfig.json', 'r') as f:
            dataConfig = json.load(f)
            f.close()
    except FileNotFoundError:
        if DEBUG: print("Config file not found.")
        dataConfig = json.loads(defaultDataConfig)
        with open(CIRprojectDirectory + '/dataConfig.json', 'w+') as f:
            json.dump(dataConfig, f)
            f.close()
    try:
        loadInput(nbPtsInput, dataConfig['nbPts'])
        loadInput(acStartFrequencyInput, dataConfig['acStartFrequency'])
        loadInput(acEndFrequencyInput, dataConfig['acEndFrequency'])

        standardLibVar.set(dataConfig['standardLib'])

        loadInput(startSavingDataInput, dataConfig['startSavingData'])
        loadInput(runToTimeInput, dataConfig['runToTime'])
        loadInput(maxStepSizeInput, dataConfig['maxStepSize'])
        uicVar.set(dataConfig['uicMode'])    

        acSweepTypeComboBox.current(dataConfig['acSweepType'])

        dcSweepType1ComboBox.current(dataConfig['dcSweepType1'])
        loadInput(dcNameSrc1Input, dataConfig['dcNameSrc1'])
        loadInput(dcStartSrc1Input, dataConfig['dcStartSrc1'])
        loadInput(dcEndSrc1Input, dataConfig['dcEndSrc1'])
        loadInput(nbPtsSrc1Input, dataConfig['nbPtsSrc1'])
        loadInput(dcListSrc1Input, dataConfig['dcListSrc1'])

        dcSweepType2ComboBox.current(dataConfig['dcSweepType2'])
        loadInput(dcNameSrc2Input, dataConfig['dcNameSrc2'])
        loadInput(dcStartSrc2Input, dataConfig['dcStartSrc2'])
        loadInput(dcEndSrc2Input, dataConfig['dcEndSrc2'])
        loadInput(nbPtsSrc2Input, dataConfig['nbPtsSrc2'])
        loadInput(dcListSrc2Input, dataConfig['dcListSrc2'])
        return True
    except KeyError:
        os.remove(CIRprojectDirectory + '/dataConfig.json')
        return False
# Load general configuration and previous data from project
while loadConfig() == False:
    loadConfig()
# Hide some Tabs if netlist is missing
if netlistExist == False:
    AllTabs.hide(transientAnalysisTab)
    AllTabs.hide(parametersTab)
    AllTabs.hide(mcWcTab)
    AllTabs.hide(opAnalysisTab)
    analysisTypeComboBox.config(state = "disabled")
    startSimulationProcessButton.config(state = "disabled")
monAppli.mainloop()