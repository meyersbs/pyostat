#!/usr/bin/env python

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
import sys
import time
import datetime
from optparse import OptionParser, OptionGroup

from pyostat_device import DeviceData
import pyostat_device

curr_version = '1.0'
mountstats_path = '/proc/self/mountstats'
usage_statement = "%prog [ <interval> ] [ <count> ] [ <option> ] [ <option> ]\n"
usage_statement += "\nDescription: Display NFS client per-mount statistics.\n"
usage_statement += "\t<interval> the amount of time (seconds) between each report.\n"
usage_statement += "\t<count> the number of reports generated at <interval> apart.\n"
usage_statement += "\t<option> the display options for stdout and file writing."
description, timestamp = '', ''
pyostat_version = 'Pyostat v%s' % curr_version
verbose_seen, display_output = False, True


class ModifiedOptionParser(OptionParser):
	def error(self, msg):
		print("Ignoring Unknown Option. Try '--help' for usage information.")
		pass


########################################################################################################################
# FUNCTIONS ############################################################################################################
########################################################################################################################
# Generates a dictionary of statistics for the specified file.
def parse_stats_file(filename):
	mountstats_dict = dict()
	key = ''

	f = open(filename)
	new = []
	for line in f.readlines():
		words = line.split()
		if len(words) == 0:
			continue

		if words[0] == 'device':
			key = words[4]
			new = [line.strip()]
		elif 'nfs' in words or 'nfs4' in words:
			key = words[3]
			new = [line.strip()]
		else:
			new += [line.strip()]

		mountstats_dict[key] = new

	return mountstats_dict


# Parses the device list to only include the intersection of old and new data. This address umounts due to autofs
# mountpoints.
def print_iostat_summary(old, new, devices):
	global timestamp
	# Tells pyostat to start collecting data.
	pyostat_device.start_collecting()
	stats, diff_stats = {}, {}

	if old:
		devicelist = [x for x in old if x in devices]
	else:
		devicelist = devices

	for device in devicelist:
		stats[device] = DeviceData()
		stats[device].parse_stats(new[device])
		if old:
			old_stats = DeviceData()
			old_stats.parse_stats(old[device])
			diff_stats[device] = stats[device].compare_iostats(old_stats)

	# Stores the timestamp for the current data.
	timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S') # <-- Weird Python Magic.
	for device in devicelist:
		if old:
			diff_stats[device].display_iostats()
		else:
			stats[device].display_iostats()

	# Tells pyostat to stop collecting data, calculate averages, save the data to a file, and print to stdout.
	pyostat_device.stop_collecting()
	pyostat_device.calculate_data(timestamp)
	pyostat_device.print_to_file()
	pyostat_device.print_to_stdout()


# Generates a list of the NFS mount points.
def list_nfs_mounts(list_param, mountstats):
	mount_list = []
	if len(list_param) > 0:
		for device in list_param:
			stats = DeviceData()
			stats.parse_stats(mountstats[device])
			if stats.is_nfs_mountpoint():
				mount_list += [device]
	else:
		for device, dev_description in mountstats.items():
			stats = DeviceData()
			stats.parse_stats(dev_description)
			if stats.is_nfs_mountpoint():
				mount_list += [device]

	return mount_list


# Parses command line arguments. Sends the command to gather statistics.
def iostat_command(prog):
	global verbose_seen, display_output
	mountstats = parse_stats_file(mountstats_path)
	original_devices = []
	interval_seen, count_seen, verbose_seen, display_output = False, False, False, True

	# Setup command line argument parser.
	parser = ModifiedOptionParser(usage=usage_statement, description=description, version=pyostat_version)
	parser.set_defaults(which=0, sort=False, list=sys.maxsize)

	display_group = OptionGroup(parser, "Display Options",
							    "Standard output is displayed in stdout unless '-q' is specified.")
	display_group.add_option('-q', '--quiet', action="store_const", dest="which", const=1,
							 help="disables all output to stdout")
	parser.add_option_group(display_group)
	verbose_group = OptionGroup(parser, "Verbose Options",
								"Standard output is written to 'all_ip_mounts.out' unless '-v' is specified.")
	verbose_group.add_option('-v', '--verbose', action="store_const", dest="which", const=1,
						     help="displays unaveraged statistics in stdout and writes them to 'all_ip_mounts.out'")
	parser.add_option_group(verbose_group)

	(options, args) = parser.parse_args(sys.argv)
	bad_interval = 'Illegal <interval> value %s'
	bad_count = 'Illegal <count> value %s'
	no_nfs_message = 'No NFS mount points were found.'
	for arg in args:
		if arg == sys.argv[0]:
			continue

		# Parses command line options.
		if len(sys.argv) == 3 and sys.argv[2] == '-q':
			display_output = False
			verbose_seen = False
		elif len(sys.argv) == 3 and sys.argv[2] == '-v':
			verbose_seen = True
		elif len(sys.argv) == 4 and sys.argv[3] == '-q':
			display_output = False
			verbose_seen = False
		elif len(sys.argv) == 4 and sys.argv[3] == '-v':
			verbose_seen = True
		elif len(sys.argv) == 5 and (sys.argv[3] == '-q' or sys.argv[4] == '-q'):
			display_output = False
			if sys.argv[3] == '-v' or sys.argv[4] == '-v':
				verbose_seen = True

		if arg in mountstats:
			original_devices += [arg]
		elif not interval_seen:
			try:
				interval = int(arg)
			except ValueError:
				print(bad_interval % arg); return
			if interval > 0:
				interval_seen = True
			else:
				print(bad_interval % arg); return
		elif not count_seen:
			try:
				count = int(arg)
			except ValueError:
				print(bad_count % arg); return
			if count > 0:
				count_seen = True
			else:
				print(bad_count % arg); return

	devices = list_nfs_mounts(original_devices, mountstats)
	if len(devices) == 0:
		print(no_nfs_message)

	old_mountstats = None

	if not interval_seen:
		print_iostat_summary(old_mountstats, mountstats, devices); return

	# Print out stats for the specified number of counts.
	if count_seen:
		while count != 0:
			print_iostat_summary(old_mountstats, mountstats, devices)
			old_mountstats = mountstats
			if display_output:
				print('#### SLEEPING ####')
				interval_count = interval
				while interval_count > 0:
					print interval_count
					time.sleep(1)
					interval_count -= 1
			else:
				time.sleep(interval)
			mountstats = parse_stats_file(mountstats_path)
			# Recheck the device list for automount adds and drops.
			devices = list_nfs_mounts(original_devices, mountstats)
			if len(devices) == 0:
				print(no_nfs_message); return
			count -= 1
	# Print out stats forever.
	else:
		while True:
			print_iostat_summary(old_mountstats, mountstats, devices)
			old_mountstats = mountstats
			if display_output:
				print('#### SLEEPING ####')
				interval_count = interval
				while interval_count > 0:
					print interval_count
					time.sleep(1)
					interval_count -= 1
			else:
				time.sleep(interval)
			mountstats = parse_stats_file(mountstats_path)
			# Recheck the device list for automount adds and drops.
			devices = list_nfs_mounts(original_devices, mountstats)
			if len(devices) == 0:
				print(no_nfs_message); return
