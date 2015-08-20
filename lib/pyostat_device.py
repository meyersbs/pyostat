#!/usr/bin/env python

from __future__ import print_function

########################################################################################################################
# DETAILS ##############################################################################################################
########################################################################################################################
# @author: 	Benjamin S. Meyers
# @email:	lion.logic.org@gmail.com
########################################################################################################################
# COPYRIGHT INFORMATION ################################################################################################
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

########################################################################################################################
# IMPORTS & GLOBAL VARIABLES ###########################################################################################
########################################################################################################################
import sys, re
import pyostat_functions

curr_read_retrans, curr_write_retrans, curr_read_rtt, curr_write_rtt, curr_ip = '', '', '', '', ''
seen_ips = []
avgs, out_files, out_data = {}, {}, {}
collecting = True
all_output_file = open('all_ip_mounts.out', 'a')
out_files['127.0.0.1'] = all_output_file
verbose_line = '##### BEGIN VERBOSE OUTPUT #####\n'


########################################################################################################################
# FUNCTIONS ############################################################################################################
########################################################################################################################
# Toggles collecting flag to True.
def start_collecting():
	global collecting
	collecting = True


# Toggles collecting flag to False.
def stop_collecting():
	global collecting
	collecting = False


# Calculates averages for all of the read/write statistics.
def calculate_data(timestamp):
	global curr_ip, avgs, out_data
	for item in avgs.keys():
		out_data[str(item)][0] = str(timestamp)
		out_data[str(item)][1] = str(item) # curr_ip
		out_data[str(item)][2] = str(float(avgs[item][0]) / float(avgs[item][4]))
		out_data[str(item)][3] = str(float(avgs[item][1]) / float(avgs[item][4]))
		out_data[str(item)][4] = str(float(avgs[item][2]) / float(avgs[item][4]))
		out_data[str(item)][5] = str(float(avgs[item][3]) / float(avgs[item][4]))

		avgs[item] = [0, 0, 0, 0, 0]


# Appends a line of Pipe-Separated-Values to the appropriate output file.
def print_to_file():
	global out_files, out_data
	for key in sorted(out_data):
		line = (out_data[key][0] + '|' + out_data[key][1] + str(len(out_data[key][6])) + '|' +
				out_data[key][2] + '|' + out_data[key][3] + '|' + out_data[key][4] + '|' +
				out_data[key][5] + '\n')
		out_files[str(key) + '.out'].write(line)
		if not pyostat_functions.verbose_seen:
			out_files['127.0.0.1'].write(line)


# Prints pretty-looking output to stdout.
def print_to_stdout():
	global out_files, out_data
	if pyostat_functions.display_output:
		for key in sorted(out_data):
			shares = str(len(out_data[key][6])) + ' NFS Share(s)'

			print('\n#################################################################')
			print(str(out_data[key][0]) + '\t' + str(out_data[key][1]) + '\t' + shares)
			print('#################################################################')
			print('\navg READ:\tretrans:\tRTT:')
			print('\t\t' + out_data[key][2] + '\t\t' + out_data[key][3])
			print('\navg WRITE:\tretrans:\tRTT:')
			print('\t\t' + out_data[key][4] + '\t\t' + out_data[key][5])


########################################################################################################################
# CLASS: DeviceData ####################################################################################################
########################################################################################################################
# Provides methods for parsing and displaying data for a single mount point.
class DeviceData:
	# Creates a DeviceData object.
	def __init__(self):
		self.__nfs_data = dict()
		self.__rpc_data = dict()
		self.__rpc_data['ops'] = []

	# Parses an NFS line into a dictionary.
	def __parse_nfs_line(self, words):
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

	# Parses an RPC line into a dictionary.
	def __parse_rpc_line(self, words):
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

	# Determines whether or not to parse the lines from a mount stat file as NFS or RPC stats.
	def parse_stats(self, lines):
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

	# Returns True if this is an NFS or NFSv4 mount point.
	def is_nfs_mountpoint(self):
		if self.__nfs_data['file_sys_type'] == 'nfs' or self.__nfs_data['file_sys_type'] == 'nfs4':
			return True
		return False

	# Returns the difference between two sets of statistics.
	def compare_iostats(self, old_stats):
		def difference(x, y):
			return x - y

		result = DeviceData()

		# Copy self into result.
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

	# Print generics stats for one RPC.
	def __print_rpc_op_stats(self, op, verbose, display, timestamp):
		global curr_read_retrans, curr_write_retrans, curr_read_rtt, curr_write_rtt, out_files, verbose_line
		if op not in self.__rpc_data:
			return

		rpc_stats = self.__rpc_data[op]
		ops = float(rpc_stats[0])
		retrans = float(rpc_stats[1] - rpc_stats[0])
		rtt = float(rpc_stats[6])

		# Prevent floating point exceptions.
		if ops != 0:
			rtt_per_op = rtt / ops
		else:
			rtt_per_op = 0.0		

		op += ':'
		retransmits = '{0:>10.0f}'.format(retrans).strip()
		if op.lower() == 'read:':
			curr_read_retrans = format(retransmits, '>16')
			curr_read_rtt = format(rtt_per_op, '>16.3f')
			if display and verbose:
				print('\n%s mounted on %s:' % (self.__nfs_data['ip_address'], self.__nfs_data['mount_point']))
				print('\nREAD:\t\tretrans:\tavg RTT:\n\t' + str(curr_read_retrans) + str(curr_read_rtt))
				verbose_line += str(timestamp) + '|' + self.__nfs_data['ip_address'].split(':')[0] + '|' + str(curr_read_rtt).lstrip()
			elif verbose:
				verbose_line += str(timestamp) + '|' + self.__nfs_data['ip_address'].split(':')[0] + '|' + str(curr_read_rtt).lstrip()
		elif op.lower() == 'write:':
			curr_write_retrans = format(retransmits, '>16')
			curr_write_rtt = format(rtt_per_op, '>16.3f')
			if display and verbose:
				print('\nWRITE:\t\tretrans:\tavg RTT:\n\t' + str(curr_write_retrans) + str(curr_write_rtt))
				verbose_line += '|' + str(curr_write_rtt).lstrip() + '|' + str(curr_read_retrans).lstrip() + '|' + str(curr_write_retrans).lstrip()
				out_files['127.0.0.1'].write(verbose_line)
				verbose_line = ''
			if verbose:
				verbose_line += '|' + str(curr_write_rtt).lstrip() + '|' + str(curr_read_retrans).lstrip() + '|' + str(curr_write_retrans).lstrip()
				out_files['127.0.0.1'].write(verbose_line)
				verbose_line = ''

	# Gets the current IP and checks if it has been seen in this iteration. If it hasn't, makes note of it and sets up
	# related variables/objects. Sets the global curr_ip to the current IP and returns it.
	def __set_curr_ip(self):
		global curr_ip, seen_ips, avgs, out_files, out_data, seen_ips
		curr_ip = self.__nfs_data['ip_address'].split(':')[0]
		if curr_ip not in seen_ips:
			seen_ips.append(curr_ip)
			avgs[curr_ip] = [0, 0, 0, 0, 0]
			out_data[str(curr_ip)] = ['', '', '', '', '', '', []]
			out_data[str(curr_ip)][6].append(str(self.__nfs_data['mount_point']).split('/')[-1])
			new_file = open(str(curr_ip) + '.out', 'a')
			out_files[new_file.name] = new_file
		else:
			if str(self.__nfs_data['mount_point']).split('/')[-1] not in out_data[str(curr_ip)][6]:
				out_data[str(curr_ip)][6].append(str(self.__nfs_data['mount_point']).split('/')[-1])
		return curr_ip

	# Collects the current data and saves it into avgs based on the current IP.
	def __collect_data(self):
		global collecting, curr_ip, curr_read_rtt, curr_write_rtt, curr_read_retrans, curr_write_retrans
		if collecting:
			avgs[curr_ip][0] += float(curr_read_rtt)
			avgs[curr_ip][1] += float(curr_write_rtt)
			avgs[curr_ip][2] += float(curr_read_retrans)
			avgs[curr_ip][3] += float(curr_write_retrans)
			avgs[curr_ip][4] += 1

	# Display NFS and RPC stats in an iostat-like way.
	def display_iostats(self):
		self.__set_curr_ip()
		self.__print_rpc_op_stats('READ', pyostat_functions.verbose_seen, pyostat_functions.display_output,
								  pyostat_functions.timestamp)
		self.__print_rpc_op_stats('WRITE', pyostat_functions.verbose_seen, pyostat_functions.display_output,
								  pyostat_functions.timestamp)
		self.__collect_data()

		sys.stdout.flush()
