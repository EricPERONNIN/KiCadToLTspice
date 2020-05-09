#! usr/bin/python
# -*- coding: utf-8 -*-

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

#  Written by : Laurent CHARRIER
#  last change: 2017, Oct 30.
#  Modified by : Eric PERONNIN
#    utf-16le file dectection
#    PIN name allways invisible
#    PIN direction R by default for compatibility with KiCad 5
# usage examples : python lib_LTspice2Kicad.py C:\Program Files\LTC\LTspiceXVII\lib\sym
#                  python lib_LTspice2Kicad.py C:\Program Files\LTC\LTspiceXVII\lib\sym\Comparators
#       Those examples will create the files : LTspice_sym.libs  and  LTspice_Comparators.libs
#

import sys,re,os,codecs
from tkinter.messagebox import *

#scale = 1.0
#XUViewPin = "Y" #N ou Y

def convertToKicad(srcDir, srcFile, defaultDestDir, destLibrary, XUViewPin, scale):
	# function to find locaion of each space character in each line
	def find_all(a_str, sub):
		start = 0
		while True:
			start = a_str.find(sub, start)
			if start == -1: return
			yield start
			start += len(sub) # use start += 1 to find overlapping matches

	def getSymbolSrc(in_file):
		# Detect if encoding is utf-8 or utf-16-le
		infl = codecs.open(in_file,"rb",'utf-16-le');
		firstWord = infl.readline(1)
		infl.close
		if ord(firstWord) < 256:
			print("utf16")
			infl = codecs.open(in_file,"r",'utf-16-le');
		else:
			print("utf8")
			infl = open(in_file,"r");

		lines = infl.readlines()
		infl.close()
		return lines

	#directory = sys.argv[1]
	#XUViewPin = sys.argv[2]
	#scale = float(sys.argv[3])
	srcDir = srcDir.replace("\\", "/")
	components = []
	directory = srcDir

	# File or directory conversion ?
	if srcFile == "":
		# Directory conversion : delete lib file if exist
		print("Directory conversion")
		if destLibrary == "":
			#No destLibrary input => create library with a name based on srcDir
			# Build file name
			i = len(srcDir)-1
			while i>0 and srcDir[i-1] != "/": i = i - 1
			while srcDir[len(srcDir)-1] == "/": srcDir = srcDir[:-1]
			out_file = defaultDestDir + "/LTspice" + srcDir[i:] + ".lib"
			print("Outfile : " + out_file)
		else:
			out_file = destLibrary
		if os.path.isfile(out_file):
			if askokcancel("Warning", "Kicad Library File already exist.\nDelete ?"):
				print("Create destination file : LTspice" + out_file)
			else: return
		outfl = codecs.open(out_file,"w",'utf-8');
		outfl.write("EESchema-LIBRARY Version 2.4\n#encoding utf-8\n#\n")
		# Write KiCad library documentation file
		outFileDoc = out_file[:-4] + ".dcm"
		fileOutDoc = open(outFileDoc, 'w', encoding='utf-8')
		fileOutDoc.write("EESchema-DOCLIB  Version 2.0\n")
		# List components in srcDir
		dir = os.listdir(directory)
		print(dir)
		for component in dir:
			if component[-4:]==".asy" : components.append(component)
	else:
		print("File conversion")
		if destLibrary == "":
			showerror("Error", "Library Destination File is missing.\nUse KiCad first to create a library.")
			return
		components.append(srcFile)
		# Check if symbol already exist in KiCad lib
		if os.path.isfile(destLibrary) == False:
			showerror("Error", "Library Destination File doesn't exist. Retry ...")
			return
		fileOut = open(destLibrary, 'r', encoding='utf-8')
		library = fileOut.readlines()
		fileOut.close()
		for line in library :
			if line.find("DEF " + srcFile[:-4] + " ") != -1 :
				showerror("Error", "Symbol is already in library.\nRun KiCad Symbol Editor, delete this component and try conversion again.")
				# Stop symbol creation
				return
		outfl = open(destLibrary, 'w+', encoding='utf-8')
		for line in library:
			if line != "#End Library\n" :
				outfl.write(line)
		fileOutDoc = open(destLibrary[:-4] + ".dcm", 'a', encoding='utf-8')

	for component in components :
		print(component)
		in_file = directory + "/" + component

		# Detect if encoding is utf-8 or utf-16-le
		infl = codecs.open(in_file,"rb",'utf-16-le');
		firstWord = infl.readline(1)
		infl.close
		if ord(firstWord) < 256:
			print("utf16")
			infl = codecs.open(in_file,"r",'utf-16-le');
		else:
			print("utf8")
			infl = open(in_file,"r");

		#if (component == "ADA4807.asy" or component == "ADA4895.asy") :  # I don't know how to detect automatically the file encoding UTF-16-LE with Python
		#	infl = codecs.open(in_file,"r",'utf-16-le');
		#else : infl = open(in_file,"r");
		lines = infl.readlines()
		infl.close()

		drw_lin = list()
		# pins stuffs
		pin_pos = []
		pin_orient = []
		pin_justif=[]
		pin_name = []
		pin_order = []
		pin_off=[]
		
		Value = "Value"
		Value_XY = "0 0"
		Value_orient = "H"
		Value_justif = "L"
		Prefix = ""
		Prefix_XY = "0 0"
		Prefix_orient = "H"
		Prefix_justif = "L"
		Description = ""
		SpiceModel = ""

		# read the LTspice library line by line :
		for line1 in lines:
			line1 = line1.rstrip('\n')
			line1 = line1.rstrip('\r')
			# print(line1)
			spc = list(find_all(line1," "))  # find all space locations to split the variables of the line
			if re.match(r"^SYMATTR Prefix *", line1) is not None: 
				Prefix = line1[15:]
			if re.match(r"^WINDOW 0 *", line1) is not None: 
				Prefix_XY = str(int(scale * 3.125*int(line1[spc[1]:spc[2]]))) + " " + str(int(-scale * 3.125*int(line1[spc[2]:spc[3]])))
				Prefix_orient = "H"
				Prefix_justif = line1[spc[3]+1:spc[3]+2]
				if Prefix_justif=="V" :
					Prefix_orient = "V"
					Prefix_justif = line1[spc[3]+2:spc[3]+3]
			if re.match(r"^SYMATTR Value *", line1) is not None: 
				Value = line1[14:]
			if re.match(r"^SYMATTR Value2 *", line1) is not None: 
				Value = line1[15:]
			if re.match(r"^WINDOW 3 *", line1) is not None: 
				Value_XY = str(int(scale * 3.125*int(line1[spc[1]:spc[2]]))) + " " + str(int(-scale * 3.125*int(line1[spc[2]:spc[3]])))
				Value_orient = "H"
				Value_justif = line1[spc[3]+1:spc[3]+2]
				if Value_justif=="V" :
					Value_orient = "V"
					Value_justif = line1[spc[3]+2:spc[3]+3]
			if re.match(r"^SYMATTR Description *", line1) is not None: 
				Description = line1[19:]
			if re.match(r"^SYMATTR SpiceModel *", line1) is not None: 
				SpiceModel = line1[18:]
			
			if re.match(r"^LINE *", line1) is not None: 
				if len(spc)==5 :
					drw_lin.append("P 2 0 0 0 " + str(int(scale * 3.125*int(line1[spc[1]:spc[2]]))) + " " + str(int(-scale * 3.125*int(line1[spc[2]:spc[3]]))) + " " + str(int(scale * 3.125*int(line1[spc[3]:spc[4]]))) + " " + str(int(-scale * 3.125*int(line1[spc[4]:]))))
				else :
					drw_lin.append("P 2 0 0 0 " + str(int(scale * 3.125*int(line1[spc[1]:spc[2]]))) + " " + str(int(-scale * 3.125*int(line1[spc[2]:spc[3]]))) + " " + str(int(scale * 3.125*int(line1[spc[3]:spc[4]]))) + " " + str(int(-scale * 3.125*int(line1[spc[4]:spc[5]]))))
					
			if re.match(r"^RECTANGLE *", line1) is not None: 
				if len(spc)==5 :
					drw_lin.append("S " + str(int(scale * 3.125*int(line1[spc[1]:spc[2]]))) + " " + str(int(-scale * 3.125*int(line1[spc[2]:spc[3]]))) + " " + str(int(scale * 3.125*int(line1[spc[3]:spc[4]]))) + " " + str(int(-scale * 3.125*int(line1[spc[4]:]))) + " 0 0 0 f")
				else :
					drw_lin.append("S " + str(int(scale * 3.125*int(line1[spc[1]:spc[2]]))) + " " + str(int(-scale * 3.125*int(line1[spc[2]:spc[3]]))) + " " + str(int(scale * 3.125*int(line1[spc[3]:spc[4]]))) + " " + str(int(-scale * 3.125*int(line1[spc[4]:spc[5]]))) + " 0 0 0 f")
			
			if re.match(r"^CIRCLE *", line1) is not None: 
				if len(spc)==5 :
					drw_lin.append("C " + str(int(0.5*scale * 3.125*(int(line1[spc[1]:spc[2]]) + int(line1[spc[3]:spc[4]])))) + " " + str(int(0.5*-scale * 3.125*(int(line1[spc[2]:spc[3]]) + int(line1[spc[4]:])))) + " " + str(int(0.5*scale * 3.125*abs(int(line1[spc[1]:spc[2]]) - int(line1[spc[3]:spc[4]])))) + " 0 0 0 N")
				else :
					drw_lin.append("C " + str(int(0.5*scale * 3.125*(int(line1[spc[1]:spc[2]]) + int(line1[spc[3]:spc[4]])))) + " " + str(int(0.5*-scale * 3.125*(int(line1[spc[2]:spc[3]]) + int(line1[spc[4]:spc[5]])))) + " " + str(int(0.5*scale * 3.125*abs(int(line1[spc[1]:spc[2]]) - int(line1[spc[3]:spc[4]])))) + " 0 0 0 N")
			
			if re.match(r"^ARC *", line1) is not None: 
				if len(spc)==9 : 
					drw_lin.append("A " + str(int(0.5*scale * 3.125*(int(line1[spc[1]:spc[2]]) + int(line1[spc[3]:spc[4]])))) + " " + str(int(0.5*-scale * 3.125*(int(line1[spc[2]:spc[3]]) + int(line1[spc[4]:spc[5]])))) + " " + str(int(0.5*scale * 3.125*abs(int(line1[spc[1]:spc[2]]) - int(line1[spc[3]:spc[4]])))) + " 0 900 0 0 0 N " + str(int(scale * 3.125*int(line1[spc[5]:spc[6]]))) + " " + str(int(-scale * 3.125*int(line1[spc[6]:spc[7]]))) + " " + str(int(scale * 3.125*int(line1[spc[7]:spc[8]]))) + " " + str(int(-scale * 3.125*int(line1[spc[8]:]))))
				else : 
					drw_lin.append("A " + str(int(0.5*scale * 3.125*(int(line1[spc[1]:spc[2]]) + int(line1[spc[3]:spc[4]])))) + " " + str(int(0.5*-scale * 3.125*(int(line1[spc[2]:spc[3]]) + int(line1[spc[4]:spc[5]])))) + " " + str(int(0.5*scale * 3.125*abs(int(line1[spc[1]:spc[2]]) - int(line1[spc[3]:spc[4]])))) + " 0 900 0 0 0 N " + str(int(scale * 3.125*int(line1[spc[5]:spc[6]]))) + " " + str(int(-scale * 3.125*int(line1[spc[6]:spc[7]]))) + " " + str(int(scale * 3.125*int(line1[spc[7]:spc[8]]))) + " " + str(int(-scale * 3.125*int(line1[spc[8]:spc[9]]))))
					
			if re.match(r"^TEXT *", line1) is not None: 
				if (line1[spc[3]+1:spc[3]+2]=="V"):
					text_orient = "1 "
					text_justif = line1[spc[3]+2:spc[3]+3]
				else :
					text_orient = "0 "
					text_justif = line1[spc[3]+1:spc[3]+2]
				drw_lin.append("T " + text_orient + str(int(scale * 3.125*int(line1[spc[0]:spc[1]]))) + " " + str(int(-scale * 3.125*int(line1[spc[1]:spc[2]]))) + " 50 0 0 1 " + "\"" + line1[spc[4]:] + "\"")
				# drw_lin.append("T " + text_orient + str(int(scale * 3.125*int(line1[spc[0]:spc[1]]))) + " " + str(int(-scale * 3.125*int(line1[spc[1]:spc[2]]))) + " 0 0 1 " + line1[spc[4]:] + " N N " + text_justif)

			if ((re.match(r"^PIN *", line1) is not None) and not(re.match(r"^PINATTR *", line1) is not None)): 
				pin_pos.append(str(int(scale * 3.125*int(line1[spc[0]:spc[1]]))) + " " + str(int(-scale * 3.125*int(line1[spc[1]:spc[2]]))))
				pin_off.append(str(int(scale * 3.125*int(line1[spc[3]:]))))
				if (line1[spc[2]+1:spc[2]+2]=="V") :
					pin_orient.append("V")
					pin_justif.append(line1[spc[2]+2:spc[2]+3])
				else :
					pin_orient.append("H")
					pin_justif.append(line1[spc[2]+1:spc[2]+2])
			if re.match(r"^PINATTR SpiceOrder *", line1) is not None:
				pin_order.append(line1[spc[1]:])
			if re.match(r"^PINATTR PinName *", line1) is not None:
				pin_name.append(line1[spc[1]:])

		# output the data in Kicad format
		outfl.write("#   " + component[0:len(component)-4] + "\n")
		if Description != "":
			Description = Description.replace('"', "")
			outfl.write("# " + Description + "\n")
		if SpiceModel != "":
			outfl.write("# SpiceModel : " + SpiceModel + "\n")
		if SpiceModel != "" or Description != "":
			fileOutDoc.write("$CMP " + component[0:len(component)-4] + "\n")
			fileOutDoc.write("D ")
			if SpiceModel != "":
				fileOutDoc.write(" Spice library : " + SpiceModel)
				if Description != "":
					fileOutDoc.write(" ")
			if Description != "":
				fileOutDoc.write(Description)
			fileOutDoc.write("\n$ENDCMP\n")

		outfl.write("#\n")
		if (Prefix=="B" or Prefix=="E" or Prefix=="F" or Prefix=="G" or Prefix=="H" or Prefix=="I" or Prefix=="V") : Pow="P"
		else : Pow="N" 
		if (Prefix=="X" or Prefix=="U"): ViewPin = XUViewPin #Même pour les circuits intégrés, les symboles ont du texte pour les noms de PIN
		else : ViewPin = "N"
		outfl.write("DEF " + component[0:len(component)-4] + " " + Prefix + " 0 1 N " + ViewPin + " 1 F " + Pow + "\n")
		if ((Prefix_justif == "B") or (Prefix_justif == "T")):
			outfl.write("F0 \"" + Prefix + "\" " + Prefix_XY + " 50 " + Prefix_orient + " V C " + Prefix_justif + "NN\n")
		else :
			outfl.write("F0 \"" + Prefix + "\" " + Prefix_XY + " 50 " + Prefix_orient + " V " + Prefix_justif + " CNN\n")
		
		if ((Value_justif == "B") or (Value_justif == "T")):
			outfl.write("F1 \"" + component[0:len(component)-4] + "\" " + Value_XY + " 50 " + Value_orient + " V C " + Value_justif + "NN\n")
		else :
			outfl.write("F1 \"" + component[0:len(component)-4] + "\" " + Value_XY + " 50 " + Value_orient + " V " + Value_justif + " CNN\n")
		# Ajout des champs supplémentaires
		#Footprint
		outfl.write("F2 \"\" 0 0 50 V I C CNN\n")
		# the value is transferd to F5 instead of F1 because F1 text should be the component name 
		outfl.write("F3 \"www.analog.com/" + Value + "\" 0 0 50 V I C CNN\n")
		outfl.write("F4 \"X\" 0 0 50 H I C CNN \"Spice_Primitive\"\n")

		if Value != "Value" :
			if SpiceModel != "":
				SpiceModelLib = "*@" + SpiceModel
			else:
				SpiceModelLib = ""
			if ((Value_justif == "B") or (Value_justif == "T")):
				outfl.write("F5 \"" + Value + SpiceModelLib + "\" " + Value_XY + " 50 " + Value_orient + " I C " + Value_justif + "NN" + " \"Spice_Model\"" + "\n")
			else :
				outfl.write("F5 \"" + Value + SpiceModelLib + "\" " + Value_XY + " 50 " + Value_orient + " I " + Value_justif + " CNN" + " \"Spice_Model\"" + "\n")
			
		else:
			outfl.write("F5 \"\" 0 0 50 V I C CNN" + " \"Spice_Model\"" + "\n")

		outfl.write("F6 \"" + Description + " " + "\" 0 0 50 V I C CNN" + " \"Information\"" + "\n")
		if SpiceModel != "":
			outfl.write("F7 \"" + " Add directive : .lib " + SpiceModel + " " + "\" 0 0 50 V I C CNN" + " \"Advice\"" + "\n")

		if (Pow=="N") : outfl.write("$FPLIST\n " + Prefix + "_*\n$ENDFPLIST\n")

		#DRAWINGS and PINS
		outfl.write("DRAW\n")
		for i in range(0,len(drw_lin)) :
			outfl.write(drw_lin[i] + "\n")

		for i in range(0,len(pin_name)) :
			pinjustif = "R" # Par défaut #pin_justif[i]
			if pin_justif[i] == "L" : pinjustif = "R"
			if pin_justif[i] == "R" : pinjustif = "L"
			if pin_justif[i] == "T" : pinjustif = "D"
			if pin_justif[i] == "B" : pinjustif = "U"
			outfl.write("X " + pin_name[i].replace(" ","") + " " + pin_order[i] + " " + pin_pos[i] + " 0 " + pinjustif + " 50 50 1 1 P\n")
			
		outfl.write("ENDDRAW\nENDDEF\n#\n")
	fileOutDoc.write("#End Doc Library\n")
	fileOutDoc.close()
	outfl.write("# End Library")
	outfl.flush()
	outfl.close()

#convertToKicad(srcDir, srcFile, defaultDestDir, destLibrary, XUViewPin, scale)
#convertToKicad("C:/Users/eric/Documents/LTspiceXVII/lib/sym", "", "C:/Users/eric/Documents/KiCadToLTspice/libForKicad", "", "Y", 1.0)
#convertToKicad("C:/Users/eric/Documents/LTspiceXVII/lib/sym/ADC", "", "C:/Users/eric/Documents/KiCadToLTspice/libForKicad", "C:/Users/eric/Documents/KiCadToLTspice/libForKicad/LTspiceADC.lib", "Y", 1.0)
