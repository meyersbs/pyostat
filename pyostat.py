#!/usr/bin/env python

##########
# Author: Benjamin S. Meyers
# Email: bsm9339@rit.edu
# Date: 08-11-2015
##########

# Imports.
import sys
import fileinput
import time
import datetime


# Global variables.
curr_ip = 0
curr_data = []
curr_read = 0
curr_write = 0
avgs = {}
all_ips = []
out_files = {}


# Get the IP Address from a given string. If the IP Address is new,
# add it to all_ips and create a new list within avgs.
def get_curr_ip(ip_block):
	global curr_ip, all_ips
	curr_ip = ip_block.split(':')[0]
	if curr_ip not in all_ips: # If this IP hasn't been seen yet
		all_ips.append(curr_ip) # Make note that we've seen it
		avgs[curr_ip] = [[], [], [], []] # read_vals, read_avg, write_vals, write_avg
		new_file = open(str(curr_ip) + '.out', 'a') # Create an output file named IP.out
		out_files[new_file.name] = new_file
	return curr_ip


def main():
	global curr_data, all_ips, curr_read, curr_write, out_files
	if len(sys.argv) == 1:
		while True:
			out_file = open('all_ips.out', 'a')
			for line in fileinput.input():
				split_line = line.split()
				if split_line != ['####', 'Sleeping', '####']: # Until we see ['####', 'Sleeping', '####']
					for item in split_line:
						curr_data.append(item) # Temporarily store the line
				else:
					# Get timestamp.
					ts = time.time()
					timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
					count = 0
					# For every 45 items in the list of input
					while count < 45 and len(curr_data) >= 45:
						curr_read = curr_data[25] # Get the current read value
						curr_write = curr_data[43] # Get the current write value
						ip = get_curr_ip(curr_data[0]) # Get the current IP Address

						# Calculate read average.
						temp_read_total = 0
						temp_read_count = 0
						avgs[ip][0].append(curr_read)
						for item in avgs[ip][0]:
							temp_read_count += 1
							temp_read_total += float(item)
						avgs[ip][1] = float(temp_read_total) / temp_read_count

						# Calculate write average.
						temp_write_total = 0
						temp_write_count = 0
						avgs[ip][2].append(curr_write)
						for item in avgs[ip][2]:
							temp_write_count += 1
							temp_write_total += float(item)
						avgs[ip][3] = float(temp_write_total) / temp_write_count

						# Print output to single file
						out_file.write(str(timestamp) + '|' + str(ip) + '|' + str(avgs[ip][1]) + '|' + str(avgs[ip][3]) + '\n')
						for item in out_files.keys(): # Print output to multiple files for each IP
							if item == str(ip) + '.out':
								out_files[item].write(str(timestamp) + '|' + str(ip) + '|' + str(avgs[ip][1]) + '|' + str(avgs[ip][3]) + '\n') # Write CSV: Timestamp|IP|Read|Write
								break	
						# Print to stdout.					
						print str(timestamp) + '|' + str(ip) + '|' + str(avgs[ip][1]) + '|' + str(avgs[ip][3])

						# Prepare data for next iteration.
						curr_data = curr_data[45:]
						count = 0
					curr_data = []
		out_file.close()
	elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
		sys.exit('Output is formatted like this:\tDate Timestamp|IP_Address|Read_Average|Write_Average')
	else:
		sys.exit('Invalid input. Try \'--help\'.')


if __name__ == "__main__":
	main()
