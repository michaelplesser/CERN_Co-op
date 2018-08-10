#!/usr/bin/python

'''
Script : vice_manager.py
Version: 1.0.8
Author : Nikitas Loukas and Michael Plesser
'''
import sys
import uhal
import argparse
from termcolor import colored
from utilities import vice_helper
from optparse  import OptionParser

uhal.setLogLevelTo(uhal.LogLevel.WARNING)

def input_arguments():
	parser = OptionParser(usage="usage: %prog [options]")
	parser.add_option("-o", "--options", action="store_true", 
		help="Use command line options instead of GUI input")
	parser.add_option("-c", "--connect_board", action="store", type="string", dest="conn", default=False,
        	help="Choose board: [VICE3,VICE5,VICE7,VICE8,VICE10]")
	parser.add_option("-r", "--run_command", action="store", type="string", dest="run", default='status', 
		help="Commands: i2c (scan), status, config, capture, clkrst (clock reset), gbtxrst (GBTx reset), mode (conf ADC mode), rmgpa (rd MGPA offsets), wmgpa (wr MGPA offsets). Default status")
	parser.add_option("-s", "--clk_source", action="store", type="string", dest="clksrc", default='int',
		help="Used with clkrst command. Choose clk source: int (internal), ext (external). Default int")
	parser.add_option("-f", "--force_adc_mode", action="store", type="string", dest="fmode", default='none',
		help="Foce ADC mode: none (leave control to FE), 0x0 (Quad ADC;80MHz DDR;2x12), 0x1 (Ecal Direct;40MHz;1x14), 0x2 (Ecal w/ Hyst;40MHz;1x14), 0x3 (Ecal Direct;80MHz DDR;1x7), 0x4 (Ecal with Hyst;80MHz DDR;1x7), 0x5 (Transparent[0-1];40MHz;2x12), 0x6 (Transparent[2-3];40MHz;2x12), 0x7 (Invalid). Default none")
	parser.add_option("-m", "--mgpa", action="store", type="string", dest="mgpa", default='a',
		help="Choose mgpa to read: a (mgpa_A), b (mgpa_B), c (mgpa_C), d (mgpa_D), e (mgpa_E). Default none")
	parser.add_option("-a", "--addr_i2c", action="store", type="string", dest="ai2c", default=0x0,
		help="Define i2c address of a device or a register. Default 0x0")
	parser.add_option("-w", "--write_i2c", action="store", type="string", dest="wi2c", default=0x0,
		help="Define 8 bit value of an i2c register. Default 0x0")
	return parser.parse_args()

def input_with_default(msg, val):	# Take an input but assign default value if entry left blank
	try: var = input(msg)		
	except SyntaxError: var = val	# Default if input left blank
	return var

def main():
	(options, args) = input_arguments()

	print colored("\n" + '='*44, 'green')
	print colored("\nWelcome to the VICE manager\n", 'green')
	print colored('='*44, 'green'),'\n'

	# Use command line flag controls
	if options.options == True: 
		try:
			vhp=vice_helper('file://addrtable/conn_vice.xml',options.conn)
			vhp.logo_id(options.conn)
		except:
			sys.exit("Oops, something went wrong with the connection, did you forget -c? Check 'vice_manager.py -h' for more info")
		print

		if options.run   == 'i2c':
			vhp.i2c_scan()
		elif options.run == 'status':
			vhp.vice_status()
		elif options.run == 'config':
			vhp.vice_config()
		elif options.run == 'capture':
			vhp.vice_capture()
		elif options.run == 'gbtxrst':
			vhp.vice_reset_gbtx()		
		elif options.run == 'clkrst':
			vhp.vice_reset_clock(options.clksrc)
		elif options.run == 'mode':
			vhp.vice_fmode(options.fmode)
		elif options.run == 'rmgpa':
			vhp.vice_rmgpas(options.mgpa)
		elif options.run == 'wmgpa':
			vhp.vice_wmgpas(options.mgpa,options.ai2c,options.wi2c)
		else:
			print "Selection not found, try 'vice_manager.py -h' for more info"
	
	# Use user-input text controls
	else:	
		# Connect the board
		board = input_with_default("Select a VICE board (Default: VICE2): ", 'VICE2')
		try: vhp = vice_helper('file://addrtable/conn_vice.xml', board)
		except: sys.exit("Error, check board name. Try 'vice_manager.py -h' for more info")
		vhp.logo_id(board)
	
		while 1:
			print '\n', colored("="*44, 'green')
			vhp.run_mode_printout()
			runopt = raw_input("Select run mode: ")
			print
			
			# Options with no input
			if runopt   == 'i2c':
				vhp.i2c_scan()
			elif runopt == 'status':
				vhp.vice_status()
			elif runopt == 'config':
				vhp.vice_config()
			elif runopt == 'capture':
				vhp.vice_capture()	
			elif runopt == 'gbtxrst':
				vhp.vice_reset_gbtx()
			# Options with user-provided input
			elif runopt == 'clkrst':
				vhp.clock_source_printout()
				clksrc = input_with_default("Select your choice: ", 'int')
				vhp.vice_reset_clock(clksrc)
			elif runopt == 'mode':
				vhp.adc_mode_printout()
				fmode  = input_with_default("Select your choice: ", 'none')
				vhp.vice_fmode(fmode)
			elif runopt == 'rmgpa' or runopt == 'wmgpa':
				vhp.mgpa_printout()
				mgpa = ''
				while (mgpa in ['a','b','c','d','e']) == False: mgpa = raw_input("Select your choice: ") 	# Loop until valid input given
				if runopt == 'wmgpa':
					ai2c = input_with_default("Define an i2c address of a device or a register   (Default 0x0): ", 0x0)		
					wi2c = input_with_default("Define an 8 bit value of an i2c register address  (Default 0x0): ", 0x0)	
					vhp.vice_wmgpas(mgpa,ai2c,wi2c)
				else:   vhp.vice_rmgpas(mgpa)	
			# Exit call
			elif runopt == 'exit' or runopt == 'quit' or runopt == 'q': # Accept common exit commands, 'exit', 'quit', 'q'
				sys.exit(0)
			else:
				print colored("Selection not found. Try again, or check 'vice_manager.py -h' for more info\n", 'red')

if __name__ == '__main__':
  main()


