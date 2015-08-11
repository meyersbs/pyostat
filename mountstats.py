#!/usr/bin/python

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


# Get the IP Address from a given string. If the IP Address is new,
# add it to all_ips and create a new list within avgs.
def get_curr_ip(ip_block):
	global curr_ip, all_ips
	curr_ip = ip_block.split(':')[0]
	if curr_ip not in all_ips:
		all_ips.append(curr_ip)
		avgs[curr_ip] = [[], [], [], []] # vals, avg, vals, avg
	return curr_ip


def main():
	global curr_data, all_ips, curr_read, curr_write
	if len(sys.argv) == 1:
		while True:
			out_file = open('mountstats.out', 'a')
			for line in fileinput.input():
				split_line = line.split()
				if split_line != ['####', 'Sleeping', '####']:
					for item in split_line:
						curr_data.append(item)
				else:
					ts = time.time()
					timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
					count = 0
					while count < 45 and len(curr_data) >= 45:
						curr_read = curr_data[25]
						curr_write = curr_data[43]
						ip = get_curr_ip(curr_data[0])

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

						# Print output.
						out_file.write(str(timestamp) + '|' + str(ip) + '|' + str(avgs[ip][1]) + '|' + str(avgs[ip][3]) + '\n')
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
