#!/usr/bin/env python

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
import sys, time, datetime
from pyostat_device import DeviceData
import pyostat_device

# GLOBAL VARIABLES #####################################################################################################
NO_NFS_MESSAGE, MOUNTSTATS_PATH, TIMESTAMP = 'No NFS mount points were found: ', '/proc/self/mountstats', ''
DISPLAY_OUTPUT = True

# FUNCTIONS ############################################################################################################
def set_display_output(flag):
	global DISPLAY_OUTPUT
	DISPLAY_OUTPUT = flag

def parse_stats_file(filename):
	""" Generates a dictionary of statistics based on the MOUNTSTATS file. """
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

def print_iostat_summary(old, new, devices):
	"""
	Parses the device list so that only the intersection of old and new data is given.
	This addresses umounts due to autofs mountpoints.
	"""
	global TIMESTAMP
	pyostat_device.start_collecting() # Start collecting data
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

	TIMESTAMP = datetime.datetime.now() # Capture timestamp for the current data
	for device in devicelist:
		if old:
			diff_stats[device].display_iostats()
		else:
			stats[device].display_iostats()

	pyostat_device.stop_collecting() # Stop collecting data
	pyostat_device.calculate_data(TIMESTAMP) # Calculate averages
	pyostat_device.print_to_syslog() # Write to /var/log/syslog.log
	pyostat_device.print_to_stdout() # Print to stdout
	pyostat_device.print_to_dev_file()

def list_nfs_mounts(list_param, mountstats):
	""" Generates a list of NFS mount points. """
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

def run_iostat(interval, count):
	""" Receives the command line arguments and sends the command to gather statistics. """
	global DISPLAY_OUTPUT, NO_NFS_MESSAGE
	mountstats = parse_stats_file(MOUNTSTATS_PATH)
	original_devices, args = [], []

	for arg in sys.argv:
		args.append(arg)
	for arg in args:
		if arg == sys.argv[0]:
			continue

		if arg in mountstats:
			original_devices += [arg]

	devices = list_nfs_mounts(original_devices, mountstats)
	if len(devices) == 0:
		print(NO_NFS_MESSAGE)

	old_mountstats = None

	if count != 0:
		while count != 0:
			print_iostat_summary(old_mountstats, mountstats, devices)
			old_mountstats = mountstats
			print('#### PYOSTAT IS RUNNING #### ' + datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
			time.sleep(interval)
			mountstats = parse_stats_file(MOUNTSTATS_PATH)
			devices = list_nfs_mounts(original_devices, mountstats) # Recheck devices for automount adds/drops
			if len(devices) == 0 and DISPLAY_OUTPUT:
				print(NO_NFS_MESSAGE + datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
			count -= 1
	else:
		while True:
			print_iostat_summary(old_mountstats, mountstats, devices)
			old_mountstats = mountstats
			print('#### PYOSTAT IS RUNNING #### ' + datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
			time.sleep(interval)
			mountstats = parse_stats_file(MOUNTSTATS_PATH)
			devices = list_nfs_mounts(original_devices, mountstats) # Recheck devices for automount adds/drops
			if len(devices) == 0 and DISPLAY_OUTPUT:
				print(NO_NFS_MESSAGE + datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
