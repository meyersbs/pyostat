#!/usr/bin/env python

from __future__ import print_function

# DETAILS ##############################################################################################################
# @author: 	Benjamin S. Meyers
# @email:	bsm9339@rit.edu
########################################################################################################################
__copyright__ = """
Copyright (C) 2015, Benjamin S. Meyers <bsm9339@rit.edu>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
MA 02110-1301 USA
"""

# IMPORTS ##############################################################################################################
import sys, re, time, syslog, os
import pyostat_functions

# GLOBAL VARIABLES #####################################################################################################
CURR_READ_RTX, CURR_WRITE_RTX, CURR_READ_RTT, CURR_WRITE_RTT, CURR_IP, STANDARD_LINE = '', '', '', '', '', ''
AVGS, OUT_DATA, SEEN_IPS = {}, {}, []
COLLECTING = True
OUTFILE = None

# FUNCTIONS ############################################################################################################
def start_collecting():
	""" Toggles collecting flag to True. """
	global COLLECTING
	COLLECTING = True

def stop_collecting():
	""" Toggles collecting flag to False. """
	global COLLECTING
	COLLECTING = False

def set_out_file(filename):
	""" Try to set an optional output file. """
	global OUTFILE
	if os.path.exists(filename):
		try:
			OUTFILE = open(filename, 'a')
		except IOError:
			sys.exit("WARNING: File '" + filename + "' not found.")
	else:
		sys.exit("WARNING: File '" + filename + "' not found.")

def calculate_data(timestamp):
	""" Calculates averages for all of the read/write statistics. """
	global CURR_IP, AVGS, OUT_DATA
	for item in AVGS.keys():
		OUT_DATA[str(item)][0] = str(int(time.mktime(timestamp.timetuple()))) # UNIX POSIX timestamp
		OUT_DATA[str(item)][1] = str(item) # CURR_IP
		try:
			OUT_DATA[str(item)][2] = str(float(AVGS[item][0]) / float(AVGS[item][4])) # READ_RTT
			OUT_DATA[str(item)][3] = str(float(AVGS[item][1]) / float(AVGS[item][4])) # WRITE_RTT
			OUT_DATA[str(item)][4] = str(float(AVGS[item][2]) / float(AVGS[item][4])) # READ_RETRANS
			OUT_DATA[str(item)][5] = str(float(AVGS[item][3]) / float(AVGS[item][4])) # WRITE_RETRANS
		except ZeroDivisionError:
			syslog.syslog(syslog.LOG_ERR, "ZeroDivisionError at " + str(int(time.mktime(timestamp.timetuple()))))
		AVGS[item] = [0, 0, 0, 0, 0]

def print_to_syslog():
	"""
	Writes data to /var/log/syslog.log in the format:
	<hostname> <nfs.data.type[IP_ADDRESS]> <UNIX_TIMESTAMP> <DATA>
	"""
	global OUT_DATA, STANDARD_LINE
	for key in sorted(OUT_DATA):
		STANDARD_LINE = ('- nfs.read.RTR[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][4])
		syslog.syslog(syslog.LOG_INFO, STANDARD_LINE)
		STANDARD_LINE = ('- nfs.read.RTT[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][2])
		syslog.syslog(syslog.LOG_INFO, STANDARD_LINE)
		STANDARD_LINE = ('- nfs.write.RTR[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][5])
		syslog.syslog(syslog.LOG_INFO, STANDARD_LINE)
		STANDARD_LINE = ('- nfs.write.RTT[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][3])
		syslog.syslog(syslog.LOG_INFO, STANDARD_LINE)
		shares = str(len(OUT_DATA[key][6]))
		STANDARD_LINE = ('- nfs.shares[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + shares)
		syslog.syslog(syslog.LOG_INFO, STANDARD_LINE)

def print_to_stdout():
	""" Prints to stdout when quiet_flag is False. """
	global OUT_DATA, STANDARD_LINE
	if pyostat_functions.DISPLAY_OUTPUT:
		for key in sorted(OUT_DATA):
			shares = str(len(OUT_DATA[key][6])) + ' NFS Share(s)'
			print('\n#################################################################')
			print(str(OUT_DATA[key][0]) + '\t' + str(OUT_DATA[key][1]) + '\t' + shares)
			print('#################################################################')
			print('\navg READ:\tretrans:\tRTT:')
			print('\t\t' + OUT_DATA[key][2] + '\t\t' + OUT_DATA[key][3])
			print('\navg WRITE:\tretrans:\tRTT:')
			print('\t\t' + OUT_DATA[key][4] + '\t\t' + OUT_DATA[key][5])
	elif not pyostat_functions.DISPLAY_OUTPUT:
		for key in sorted(OUT_DATA):
			STANDARD_LINE = ('- nfs.read.RTR[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][4])
			print(STANDARD_LINE)
			STANDARD_LINE = ('- nfs.read.RTT[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][2])
			print(STANDARD_LINE)
			STANDARD_LINE = ('- nfs.write.RTR[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][5])
			print(STANDARD_LINE)
			STANDARD_LINE = ('- nfs.write.RTT[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][3])
			print(STANDARD_LINE)
			shares = str(len(OUT_DATA[key][6]))
			STANDARD_LINE = ('- nfs.shares[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + shares)
			print(STANDARD_LINE)

def print_to_dev_file():
	global OUT_DATA, STANDARD_LINE, OUTFILE
	if OUTFILE is None:
		return
	else:
		for key in sorted(OUT_DATA):
			STANDARD_LINE = ('- nfs.read.RTR[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][4] + '\n')
			OUTFILE.write(STANDARD_LINE)
			STANDARD_LINE = ('- nfs.read.RTT[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][2] + '\n')
			OUTFILE.write(STANDARD_LINE)
			STANDARD_LINE = ('- nfs.write.RTR[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][5] + '\n')
			OUTFILE.write(STANDARD_LINE)
			STANDARD_LINE = ('- nfs.write.RTT[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + OUT_DATA[key][3] + '\n')
			OUTFILE.write(STANDARD_LINE)
			shares = str(len(OUT_DATA[key][6]))
			STANDARD_LINE = ('- nfs.shares[' + OUT_DATA[key][1] + '] ' + OUT_DATA[key][0] + ' ' + shares + '\n')
			OUTFILE.write(STANDARD_LINE)

# CLASS: DeviceData ####################################################################################################
class DeviceData:
	""" Provides functions for parsing and displaying data for a single mount point. """
	def __init__(self):
		self.__nfs_data = dict()
		self.__rpc_data = dict()
		self.__rpc_data['ops'] = []

	def __parse_nfs_line(self, words):
		""" Parses an NFS line into a dictionary. """
		if words[0] == 'device':
			if re.match(r'(^(?:\d{1,3}\.){3}\d{1,3})', str(words[1])):
				self.__nfs_data['ip_address'] = words[1]
				self.__nfs_data['mount_point'] = words[4]
				self.__nfs_data['file_sys_type'] = words[7]
				if words[7] == 'nfs':
					self.__nfs_data['stats_version'] = words[8]
			else:
				self.__nfs_data['file_sys_type'] = 'IGNORE_ME'
		elif 'nfs' in words or 'nfs4' in words:
			self.__nfs_data['ip_address'] = words[0]
			self.__nfs_data['mount_point'] = words[3]
			self.__nfs_data['file_sys_type'] = words[6]
			if words[6] == 'nfs':
				self.__nfs_data['stats_version'] = words[7]

	def __parse_rpc_line(self, words):
		""" Parses an RPC line into a dictionary. """
		if words[0] == 'RPC':
			self.__rpc_data['iostats_version'] = float(words[3])
		elif words[0] == 'xprt:':
			self.__rpc_data['protocol'] = words[1]
			if words[1] == 'udp':
				self.__rpc_data['rpcsends'] = int(words[4])
				self.__rpc_data['backlogutil'] = int(words[8])
			elif words[1] == 'tcp':
				self.__rpc_data['rpcsends'] = int(words[7])
				self.__rpc_data['backlogutil'] = int(words[11])
		elif words[0] == 'per-op':
			self.__rpc_data['per-op'] = words
		else:
			op = words[0][:-1]
			self.__rpc_data['ops'] += [op]
			self.__rpc_data[op] = [int(word) for word in words[1:]]

	def parse_stats(self, lines):
		""" Determines whether or not to parse the lines from a mount stat file as NFS or RPC stats. """
		found = False
		for line in lines:
			words = line.split()
			if len(words) == 0:
				continue
			if not found and words[0] != 'RPC':
				self.__parse_nfs_line(words)
				continue

			found = True
			self.__parse_rpc_line(words)

	def is_nfs_mountpoint(self):
		""" Returns True if this is an NFS or NFSv4 mount point. """
		if self.__nfs_data['file_sys_type'] == 'nfs' or self.__nfs_data['file_sys_type'] == 'nfs4':
			return True
		return False

	def compare_iostats(self, old_stats):
		""" Returns the difference between two sets of statistics. """
		def difference(x, y):
			return x - y

		result = DeviceData()
		for key, value in self.__nfs_data.items():
			result.__nfs_data[key] = value
		for key, value in self.__rpc_data.items():
			result.__rpc_data[key] = value

		# Computes the difference between each item in the list. Note the copy loop above does not copy the lists, just
		# the reference to them. So we build new lists here for the result object.
		for op in result.__rpc_data['ops']:
			result.__rpc_data[op] = list(map(difference, self.__rpc_data[op], old_stats.__rpc_data[op]))

		# Update the remaining keys.
		result.__rpc_data['rpcsends'] -= old_stats.__rpc_data['rpcsends']
		result.__rpc_data['backlogutil'] -= old_stats.__rpc_data['backlogutil']

		return result

	def __print_rpc_op_stats(self, op):
		""" Gathers generics stats for one RPC. """
		global CURR_READ_RTX, CURR_WRITE_RTX, CURR_READ_RTT, CURR_WRITE_RTT, STANDARD_LINE
		if op not in self.__rpc_data:
			return

		rpc_stats = self.__rpc_data[op]
		ops = float(rpc_stats[0])
		retrans = float(rpc_stats[1] - rpc_stats[0])
		rtt = float(rpc_stats[6])

		if ops != 0: # Prevents floating point exceptions
			rtt_per_op = rtt / ops
		else:
			rtt_per_op = 0.0		

		op += ':'
		retransmits = '{0:>10.0f}'.format(retrans).strip()
		if op.lower() == 'read:':
			CURR_READ_RTX = format(retransmits, '>16')
			CURR_READ_RTT = format(rtt_per_op, '>16.8f')
		elif op.lower() == 'write:':
			CURR_WRITE_RTX = format(retransmits, '>16')
			CURR_WRITE_RTT = format(rtt_per_op, '>16.8f')

	def __set_curr_ip(self):
		"""
		Gets the current IP and checks if it has been seen in this iteration.
		If it hasn't, makes note of it and sets up related variables/objects.
		Sets the global curr_ip to the current IP and returns it.
		"""
		global CURR_IP, SEEN_IPS, AVGS, OUT_DATA, SEEN_IPS
		CURR_IP = self.__nfs_data['ip_address'].split(':')[0]
		if CURR_IP not in SEEN_IPS:
			SEEN_IPS.append(CURR_IP)
			AVGS[CURR_IP] = [0, 0, 0, 0, 0]
			OUT_DATA[str(CURR_IP)] = ['', '', '', '', '', '', []]
			OUT_DATA[str(CURR_IP)][6].append(str(self.__nfs_data['mount_point']).split('/')[-1])
		else:
			if str(self.__nfs_data['mount_point']).split('/')[-1] not in OUT_DATA[str(CURR_IP)][6]:
				OUT_DATA[str(CURR_IP)][6].append(str(self.__nfs_data['mount_point']).split('/')[-1])

		return CURR_IP

	@staticmethod
	def __collect_data():
		""" Collects the current data and saves it into avgs based on the current IP. """
		global COLLECTING, CURR_IP, CURR_READ_RTT, CURR_WRITE_RTT, CURR_READ_RTX, CURR_WRITE_RTX
		if COLLECTING:
			AVGS[CURR_IP][0] += float(CURR_READ_RTT)
			AVGS[CURR_IP][1] += float(CURR_WRITE_RTT)
			AVGS[CURR_IP][2] += float(CURR_READ_RTX)
			AVGS[CURR_IP][3] += float(CURR_WRITE_RTX)
			AVGS[CURR_IP][4] += 1

	def display_iostats(self):
		""" Displays NFS and RPC stats in an iostat-like way. """
		self.__set_curr_ip()
		self.__print_rpc_op_stats('READ')
		self.__print_rpc_op_stats('WRITE')
		self.__collect_data()

		sys.stdout.flush()
