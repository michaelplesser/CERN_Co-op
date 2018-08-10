#!/usr/bin/python

'''
Script : vice_helper.py
Version: 1.0.8
Author : Nikitas Loukas and Michael Plesser
'''

import os
import sys
import uhal
import time
from termcolor import colored

import csv

I2C_START = 0x80
I2C_STOP  = 0x40
I2C_RD    = 0x20
I2C_WR    = 0x10
I2C_NACK  = 0x08

GENERAL_REG = 0x00
OFFSET0_REG = 0x01
OFFSET1_REG = 0x02
OFFSET2_REG = 0x03
OFFSET3_REG = 0x04
DACCAL_REG  = 0x05

MGPAa_DEVICE = 0x79
MGPAb_DEVICE = 0x7a
MGPAc_DEVICE = 0x7b
MGPAd_DEVICE = 0x7c
MGPAe_DEVICE = 0x7d

class viceException(Exception):
	# Attributes: msg  -- explanation of the error
	def __init__(self, msg):
		self.msg = msg
	def __str__(self):
		return self.msg

class vice_helper:

	def __init__(self,connection="file://connection.xml",device="vice"):
		self._manager=uhal.ConnectionManager(connection)
		self._hw=self._manager.getDevice(device)

		# I2C registers
		self._i2c_master    = self._hw.getNode("ctrl.i2c")
		self._i2c_pre_lo    = self._i2c_master.getNode("i2c_pre_lo")
		self._i2c_pre_hi    = self._i2c_master.getNode("i2c_pre_hi")
		self._i2c_ctrl      = self._i2c_master.getNode("i2c_ctrl")
		self._i2c_rxtx      = self._i2c_master.getNode("i2c_rxtx")
		self._i2c_cmdstatus = self._i2c_master.getNode("i2c_cmdstatus")

		# Memory registers
		self._datapath = self._hw.getNode("datapath")
		self._capture  = self._datapath.getNode("mem_cnf.ctrl.capture")
		self._ch0_mode = self._datapath.getNode("mem_cnf.ctrl.modes.ch0_mode")
		self._ch1_mode = self._datapath.getNode("mem_cnf.ctrl.modes.ch1_mode")
		self._ch2_mode = self._datapath.getNode("mem_cnf.ctrl.modes.ch2_mode")
		self._ch3_mode = self._datapath.getNode("mem_cnf.ctrl.modes.ch3_mode")
		self._ch4_mode = self._datapath.getNode("mem_cnf.ctrl.modes.ch4_mode")
		self._ch0_mem  = self._datapath.getNode("ch0_mem")
		self._ch1_mem  = self._datapath.getNode("ch1_mem")
		self._ch2_mem  = self._datapath.getNode("ch2_mem")
		self._ch3_mem  = self._datapath.getNode("ch3_mem")
		self._ch4_mem  = self._datapath.getNode("ch4_mem")

		# Firmware version info
		self._fw_version = self._hw.getNode("ctrl.ver")
		self._fw_val     = self._fw_version.read()
		self._hw.dispatch()
		self._nn = '{0:08x}'.format(int(self._fw_val.value()))[6:8]
		self._dd = '{0:08x}'.format(int(self._fw_val.value()))[4:6]
		self._mm = '{0:08x}'.format(int(self._fw_val.value()))[2:4]
		self._yy = '{0:08x}'.format(int(self._fw_val.value()))[0:2]

		# STAT/CTRL registers
		self._control 	  = self._hw.getNode("ctrl.conf.ctrl")
		self._nuke 	  = self._control.getNode("nuke")
		self._soft_rst    = self._control.getNode("soft_rst")
		self._rst40 	  = self._control.getNode("rst40")
		self._clk_sel 	  = self._control.getNode("clk_sel")
		self._sel_mode    = self._control.getNode("sel_mode")
		self._force_mode  = self._control.getNode("force_mode")
		self._gpio 	  = self._control.getNode("gpio")

		self._status 	  = self._hw.getNode("ctrl.conf.stat")
		self._addr 	  = self._status.getNode("addr")
		self._mmcm_locked = self._status.getNode("mmcm_locked")

		self.i2c_init()

# Print outs
	def logo_id(self,board):
		print
		print colored('='*44, 'green')
		print colored('__     _____ ____ _____ ', 'green')
		print colored('\ \   / /_ _/ ___| ____|', 'green')
		print colored(' \ \ / / | | |   |  _|  ', 'green')
		print colored('  \ V /  | | |___| |___ ', 'green')
		print colored('   \_/  |___\____|_____|', 'green')
		print colored('-'*44, 'green')
		print colored('--> Successful connected to '+board+' <--', 'green')
		print colored('-'*44, 'green')
		sn_val = self._addr.read()
		self._hw.dispatch()
		print colored("Board SN:   %d" % (sn_val.value()),                     'blue')
		print colored("Board IP:   192.168.8.%d " % (0x10+sn_val.value()),     'blue')
		print colored("FW version: v1_%s_%s" % (self._nn[0],self._nn[1]),      'blue')
		print colored("FW builded: %s/%s/20%s" % (self._dd,self._mm,self._yy), 'blue')
		print colored('='*44, 'green')

	def run_mode_printout(self):
		print "Choose run mode:\n"
		print "\t i2c     \t\t Scanning"
		print "\t status  \t\t Display board status"
		print "\t config  \t\t Configure clock source and ADC mode"
		print "\t capture \t\t Capture data"
		print "\t clkrst  \t\t Clock reset"
		print "\t gbtxrst \t\t GBTx reset"
		print "\t mode    \t\t Configure ADC mode"
		print "\t rmgpa   \t\t Read MGPA offsets"
		print "\t wmgpa   \t\t Write MGPA offsets"
		print "\t exit, quit, q \t\t Quit the VICE manager"
		print "\t\t Default: status\n"

	def clock_source_printout(self):
		print "Available clock sources:\n"
		print "\t int \t\t (internal)"
		print "\t ext \t\t (external)"
		print "\t Default: int\n"

	def adc_mode_printout(self):
		print "Input ADC mode:\n"
		print "\t none \t(leave control to FE)"
		print "\t 0x0 \t(Quad ADC;80MHz DDR;2x12)"
		print "\t 0x1 \t(Ecal Direct;40MHz;1x14)"
		print "\t 0x2 \t(Ecal with Hyst;40MHz;1x14)"
		print "\t 0x3 \t(Ecal Direct;80MHz DDR;1x7)"
		print "\t 0x4 \t(Ecal with Hyst;80MHz DDR;1x7)"
		print "\t 0x5 \t(Transparent[0-1];40MHz;2x12)"
		print "\t 0x6 \t(Transparent[2-3];40MHz;2x12)"
		print "\t 0x7 \t(Invalid)"
		print "\t Default: none\n"

	def mgpa_printout(self):
		print "Choose mgpa to read:\n"
		print "\t a \t(mgpa_A)"
		print "\t b \t(mgpa_B)"
		print "\t c \t(mgpa_C)"
		print "\t d \t(mgpa_D)"
		print "\t e \t(mgpa_E)\n"

# Control functions
	def vice_status(self):
		sn_val 		= self._addr.read()		
		clk_sel_val 	= self._clk_sel.read()
		sel_mode_val    = self._sel_mode.read()
		force_mode_val  = self._force_mode.read()
		mmcm_locked_val = self._mmcm_locked.read()
		self._hw.dispatch()

		print colored("Printing status ...\n",'green')
		print colored(44*"=",'green')
		print colored("STATUS of SN: %01x --> IP: 192.168.8.%d " % (sn_val.value(), (sn_val.value())),'green')
		print colored(44*"-",'green')
		print colored("Firmware version: v1_%s_%s   Date: %s/%s/20%s" % (self._nn[0],self._nn[1],self._dd,self._mm,self._yy))
		print colored(44*"-",'green')
		print colored("LHC CLOCK SOURCE ext_1, int_0\t: 0x%01x" %(clk_sel_val.value()),    'blue')
		print colored("MMCM LOCKED yes_1, no_0\t\t: 0x%01x" %(mmcm_locked_val.value()),    'blue')
		print colored("ADC FORCED yes_1, no_0\t\t: 0x%01x" %(force_mode_val.value()),      'blue')
		print colored("ADC MODE (valid when FORCED==1)\t: 0x%01x" %(sel_mode_val.value()), 'blue')
		print colored(44*"=",'green')
		print
		raw_input("Press enter to continue")

	def vice_config(self):
		print colored("\nEnter the new configuration parameters",'yellow')

		try: clk_source_hex = hex(input('Enter lhc clock source (Default: int): ext=1 int=0: '))
		except SyntaxError: clk_source_hex = hex(0)						# Default if input left blank
		try: force_mode_hex = hex(input('Force ADC mode? (Default: no) yes=1 no=0: '))
		except SyntaxError: force_mode_hex = hex(0)						# Default if input left blank
		try: sel_mode_hex   = hex(input('Select ADC mode 0-7 (Recommended value: 7): '))
		except SyntaxError: sel_mode_hex   = hex(7)						# Default if input left blank

		self._rst40.write(0x1)
		self._hw.dispatch()
		self._clk_sel.write(int(clk_source_hex,16))
		self._force_mode.write(int(force_mode_hex,16))
		self._hw.dispatch()
		self._force_mode.write(1)
		self._sel_mode.write(int(sel_mode_hex,16))
		self._hw.dispatch()
		self._sel_mode.write(int(7)) # Warning: Despites its name, "mode" is ADC enable mode[2:0].
		self._hw.dispatch()
		
		self._rst40.write(0x0)
		self._hw.dispatch()
		print colored("\nReseting clocks ...",'yellow')
		os.system("sleep 0.5")
		
		lhc_clk_rst_val = self._rst40.read()
		lhc_clk_src_val = self._clk_sel.read()
		lhc_clk_lck_val = self._mmcm_locked.read()
		sn_val = self._addr.read()
		self._hw.dispatch()

		if lhc_clk_lck_val == 1:
			print colored("MMCM locked",'blue')
		else:
			print colored("MMCM Locked failed!",'red')

		self.vice_status()
		print

	def vice_capture(self):
		rd_bxs = ''
		while len(rd_bxs)==0: rd_bxs = raw_input("Enter number of bunch crossing frames to print:  ") 							# Loop until valid input given
		
		print colored("\nEnter vice running mode",'yellow')
		fe_ch_mode_hex = ''
		while len(fe_ch_mode_hex)==0: fe_ch_mode_hex = raw_input('VFEdata_0, Fixed_pattern_1, Counter_2, MyValue_3, injectBram_4, VFEdata_others :  ')	# Loop until valid input given
		self._ch0_mem.write(int(fe_ch_mode_hex,16))
		self._ch1_mem.write(int(fe_ch_mode_hex,16))
		self._ch2_mem.write(int(fe_ch_mode_hex,16))
		self._ch3_mem.write(int(fe_ch_mode_hex,16))
		self._ch4_mem.write(int(fe_ch_mode_hex,16))
		self._hw.dispatch()

		self._capture.write(0x1)
		self._hw.dispatch()
		os.system("sleep 0.1")
	
		self._capture.write(0x0)
		self._hw.dispatch()

		# Capture the data
		rd_bxs = int(rd_bxs)
		memdata = [     [],            [],            [],            [],            []      ]	 # Array to read data into
		memlist = [self._ch0_mem, self._ch1_mem, self._ch2_mem, self._ch3_mem, self._ch4_mem]	 # Array of nodes to be read
		for register in memlist:						# Iterate over the registers and read the block specified
			memdata[memlist.index(register)] = register.readBlock(rd_bxs) 	# memlist.index(register) gives the current index, and uses the same for memdata
			self._hw.dispatch()

		# Print the data
		addr = 0
		print '\n\t\tCH0  CH1  CH2  CH3  CH4'
		for i in range(addr,rd_bxs):
			print ' bunch#',addr+1,   '\t',
			for j in range(len(memdata)):
				print '{0:08x}'.format(int(memdata[j][i]))[4:8],
			print
			addr=addr+1
		print
		raw_input("Press enter to continue")

	def vice_reset_clock(self,clksrc):
		self._rst40.write(0x1)
		self._hw.dispatch()
		if    clksrc == 'int':   self._clk_sel.write(0x0)
		elif  clksrc == 'ext':   self._clk_sel.write(0x1)
		else: sys.exit("Invalid clock source. Valid choices are: int, ext \nAborting...\n ")
		self._hw.dispatch()
		
		print colored("\nReseting 40 MHz clock ...\n",'yellow')
		self._rst40.write(0x0)
		self._hw.dispatch()

		self.vice_status()

	def vice_reset_gbtx(self):
		self._gpio.write(0x0)
		self._hw.dispatch()
		print colored("Reseting GBTx chip ...",'yellow')
		os.system("sleep 0.5")
		
		self._gpio.write(0xf)
		self._hw.dispatch()
		print colored("GBTx chip reset",'green')

		self.vice_status()

	def vice_fmode(self,f_mode):
		print
		if f_mode == 'none':
			self._force_mode.write(0x0)
		else:
			self._force_mode.write(0x1)
			mode_list = [str(hex(x)) for x in range(0,8)] # Allowed options, 0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7
			while (f_mode in mode_list) == False:  f_mode = raw_input("Invalid mode option: %s. Valid are: none,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7. Try again: "%f_mode )		
			self._sel_mode.write(int(f_mode,16))
		self._hw.dispatch()
		print colored("Force ADC mode to: %s "%f_mode,'green')

		self.vice_status()

	def vice_rmgpas(self,rmgpas):
		print  colored("Reading MPGA "+rmgpas+" i2c registers ...", 'green'),'\n'
		if    rmgpas == 'a': MGPA_DEVICE = MGPAa_DEVICE
		elif  rmgpas == 'b': MGPA_DEVICE = MGPAb_DEVICE
		elif  rmgpas == 'c': MGPA_DEVICE = MGPAb_DEVICE
		elif  rmgpas == 'd': MGPA_DEVICE = MGPAb_DEVICE
		elif  rmgpas == 'e': MGPA_DEVICE = MGPAb_DEVICE
		else: sys.exit("Invalid MGPA ID: "+rmgpas)
		general=self._i2c_read_reg(MGPA_DEVICE,GENERAL_REG)
		offset0=self._i2c_read_reg(MGPA_DEVICE,OFFSET0_REG)
		offset1=self._i2c_read_reg(MGPA_DEVICE,OFFSET1_REG)
		offset2=self._i2c_read_reg(MGPA_DEVICE,OFFSET2_REG)
		daqcal =self._i2c_read_reg(MGPA_DEVICE,DACCAL_REG )
		print colored("Calibrate pulse enable of MGPA %s is:\t\t 0x%02x"         %(rmgpas,general),'blue')
		print colored("Low gain channel offset current of MGPA %s is:\t 0x%02x"  %(rmgpas,offset0),'blue')
		print colored("Mid gain channel offset current of MGPA %s is:\t 0x%02x"  %(rmgpas,offset1),'blue')
		print colored("High gain channel offset current of MGPA %s is:\t 0x%02x" %(rmgpas,offset2),'blue')
		print colored("Calibration pulse magnitude of MGPA %s is:\t 0x%02x \n"   %(rmgpas,daqcal ),'blue')
		raw_input("Press enter to continue")

	def vice_wmgpas(self,wmgpas,regaddr,regvalue):
		print  colored("Writing MPGA %s register address %s the value %s " %(wmgpas,hex(regaddr),hex(regvalue)),'green')
		if   wmgpas == 'a': self._i2c_write_reg(MGPAa_DEVICE,regaddr,regvalue)
		elif wmgpas == 'b': self._i2c_write_reg(MGPAb_DEVICE,regaddr,regvalue)
		elif wmgpas == 'c': self._i2c_write_reg(MGPAc_DEVICE,regaddr,regvalue)
		elif wmgpas == 'd': self._i2c_write_reg(MGPAd_DEVICE,regaddr,regvalue)
		elif wmgpas == 'e': self._i2c_write_reg(MGPAe_DEVICE,regaddr,regvalue)
		else:
			sys.exit("Invalid MGPA ID: %s"%wmgpas )
		self.vice_rmgpas(wmgpas)


# I2C related functions
	def i2c_init(self):
		prescaler = 0x80
		self._i2c_pre_lo.write(prescaler&0xff)
		self._i2c_pre_hi.write((prescaler>>8)&0xff)
		self._i2c_ctrl.write(0x80)
		self._hw.dispatch()
		self._i2c_cmdstatus.write(I2C_STOP)
		self._hw.dispatch()

	def _i2c_wait_ready(self):
		start_time = time.time()
		timeout    = 3	# Timeout length (in seconds)
		while time.time()-start_time < timeout:
			time.sleep(0.002)
			val = self._i2c_cmdstatus.read()
			self._hw.dispatch()
			if not val&0x2:
				return int(val)
		print colored("I2C timeout, aborting...",'red')
		sys.exit(0)

	def i2c_scan(self):
		print colored("Scanning i2c addresses ... \n", 'yellow')
		for deviceAddr in range(128):
			self._i2c_rxtx.write((deviceAddr<<1)|0x0) # LSB method, 0x0 indicates the 7 bit deviceAddr will be written to, for a total of 8 bits (1 byte)
			self._i2c_cmdstatus.write(0xD0)		  # send a start, stop, and read signal
			self._hw.dispatch()
			val=self._i2c_wait_ready()

			if not val&0x2 :
				if val&0x80:	pass
				else:		print "0x%02x ACK"%deviceAddr
			self._i2c_cmdstatus.write(I2C_STOP)
		print
		raw_input("Press enter to continue")

	def _i2c_write_reg(self,deviceAddr,regAddr,regVal):
		self._i2c_rxtx.write((deviceAddr<<1)|0x0) # LSB method, 0x0 indicates the 7 bit deviceAddr will be written to, for a total of 8 bits (1 byte)
		self._i2c_cmdstatus.write(I2C_START|I2C_WR)
		self._hw.dispatch()
		val=self._i2c_wait_ready()
		if val&0x80:  raise viceException("I2C Write register: Device 0x%02x not present."%deviceAddr)

		self._i2c_rxtx.write(regAddr)
		self._i2c_cmdstatus.write(I2C_WR)
		self._hw.dispatch()
		val=self._i2c_wait_ready()
		if val&0x80:  raise viceException("I2C Write register: Device 0x%02x not present."%deviceAddr)

		self._i2c_rxtx.write(regVal)
		self._i2c_cmdstatus.write(I2C_WR|I2C_STOP)
		self._hw.dispatch()
		val=self._i2c_wait_ready()
		if val&0x80:  print "0c Device 0x%02x not present."%deviceAddr

		return

	def _i2c_read_reg(self,deviceAddr,regAddr):
		self._i2c_rxtx.write((deviceAddr<<1)|0x0) # LSB method, 0x0 indicates the 7 bit deviceAddr will be written to, for a total of 8 bits (1 byte)
		self._i2c_cmdstatus.write(I2C_START|I2C_WR)
		self._hw.dispatch()
		val=self._i2c_wait_ready()
		if val&0x80:  raise viceException("Device 0x%02x not present."%deviceAddr)

		self._i2c_rxtx.write(regAddr)
		self._i2c_cmdstatus.write(I2C_WR)
		self._hw.dispatch()
		val=self._i2c_wait_ready()
		if val&0x80:  raise viceException("Device 0x%02x not present."%deviceAddr)

		self._i2c_rxtx.write((deviceAddr<<1)|0x1) # LSB method, 0x1 indicates the 7 bit deviceAddr will be read from, for a total of 8 bits (1 byte)
		self._i2c_cmdstatus.write(I2C_START|I2C_WR)
		self._hw.dispatch()
		val=self._i2c_wait_ready()
		if val&0x80:  raise viceException("Device 0x%02x not present."%deviceAddr)

		self._i2c_cmdstatus.write(I2C_RD|I2C_NACK)
		self._hw.dispatch()
		val=self._i2c_wait_ready()
		regval=self._i2c_rxtx.read()
		self._hw.dispatch()

		self._i2c_cmdstatus.write(I2C_STOP)
		self._hw.dispatch()
		val=self._i2c_wait_ready()

		return int(regval)

