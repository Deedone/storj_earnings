# -*- coding: utf-8 -*-
# Version: 4.0.1

from datetime import datetime

import math
import os
import subprocess
import sys

if len(sys.argv) > 3:
	sys.exit('ERROR: No more than two argument allowed. \nIf your path contains spaces use quotes. \nExample: python ' + sys.argv[0] + ' "' + os.getcwd() + '"')

if len(sys.argv) < 2:
	configPath = os.getcwd()
else:
    configPath = sys.argv[1]

if os.path.exists(configPath) == False:
	sys.exit('ERROR: Path does not exist: "' + configPath + '"')

dbPath = os.path.join(configPath,"storage","info.db")
dbDirectPath = os.path.join(configPath,"info.db")

if os.path.isfile(dbDirectPath) == True:
    dbPath=dbDirectPath

if os.path.isfile(dbPath) == False:
	sys.exit('ERROR: info.db not found at: "' + dbPath + '" or "' + dbDirectPath + '". \nEnter the correct path for your Storj config directory as a parameter. \nExample: python ' + sys.argv[0] + ' "' + os.getcwd() + '"')

if len(sys.argv) == 3:
	try:
		mdate = datetime.strptime(sys.argv[2], '%Y-%m')
	except:
		sys.exit('ERROR: Invalid month argument. \nUse YYYY-MM as format. \nExample: python ' + sys.argv[0] + ' "' + os.getcwd() + '" "' + datetime.now().strftime('%Y-%m') + '"')
else:
	mdate = datetime.now()

def formatSize(size):
    "Formats size to be displayed in the most fitting unit"
    power = math.floor((len(str(abs(int(size))))-1)/3)
    units = {
            0: " B",
            1: "KB",
            2: "MB",
            3: "GB",
            4: "TB",
            5: "PB",
            6: "EB",
            7: "ZB",
            8: "YB"
        }
    unit = units.get(power)
    sizeForm = size / (1000.00**power)
    return "{:9.2f} {}".format(sizeForm, unit)

date_from = datetime(mdate.year, mdate.month, 1)
date_to = datetime(mdate.year + int(mdate.month / 12), ((mdate.month % 12) + 1), 1)

time_window = "created_at >= '" + date_from.strftime("%Y-%m-%d") + "' AND created_at < '" + date_to.strftime("%Y-%m-%d") + "'"

if len(sys.argv) != 3:   
    satellites = 'SELECT satellite_id FROM bandwidth_usage WHERE ' + time_window + 'UNION SELECT satellite_id FROM pieceinfo'
else:
    satellites = 'SELECT DISTINCT satellite_id FROM bandwidth_usage WHERE ' + time_window

cmd = ('sqlite3 ' + dbPath + ' "SELECT hex(x.satellite_id) satellite'
    ' ,COALESCE(a.put_total,0) put_total'
    ' ,COALESCE(a.get_total,0) get_total'
    ' ,COALESCE(a.get_audit_total,0) get_audit_total'
    ' ,COALESCE(a.get_repair_total,0) get_repair_total'
    ' ,COALESCE(a.put_repair_total,0) put_repair_total'
    ' ,COALESCE(b.disk_total,0) disk_total'
    ' FROM ('
    + satellites +
    ' ) x'
    ' LEFT JOIN ('
    '   SELECT'
    '   satellite_id'
    '   ,SUM(piece_size) disk_total'
    '   FROM pieceinfo'
    '   GROUP BY satellite_id'
    ' ) b'
    ' ON x.satellite_id = b.satellite_id'
    ' LEFT JOIN ('
    '   SELECT'
    '   satellite_id'
    '   ,SUM(CASE WHEN action = 1 THEN amount ELSE 0 END) put_total'
    '   ,SUM(CASE WHEN action = 2 THEN amount ELSE 0 END) get_total'
    '   ,SUM(CASE WHEN action = 3 THEN amount ELSE 0 END) get_audit_total'
    '   ,SUM(CASE WHEN action = 4 THEN amount ELSE 0 END) get_repair_total'
    '   ,SUM(CASE WHEN action = 5 THEN amount ELSE 0 END) put_repair_total'
    '   FROM bandwidth_usage'
    '   WHERE ' + time_window +
    '   GROUP BY satellite_id'
    ' ) a'
    ' ON x.satellite_id = a.satellite_id'
    ' ORDER BY satellite;"')

p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

put_total = 0
get_total = 0
get_audit_total = 0
get_repair_total = 0
put_repair_total = 0
disk_total = 0

put = list()
get = list()
get_audit = list()
get_repair = list()
put_repair = list()
disk = list()
sums = list()

usd_get = list()
usd_get_audit = list()
usd_get_repair = list()
usd_disk = list()
usd_sum = list()

outs, errs = p.communicate()

for line in outs.splitlines():
    data = line.split('|')
    put_total = put_total + int(data[1])
    get_total = get_total + int(data[2])
    get_audit_total = get_audit_total + int(data[3])
    get_repair_total = get_repair_total + int(data[4])
    put_repair_total = put_repair_total + int(data[5])
    if len(sys.argv) != 3:   
        disk_total = disk_total + int(data[6])

    #by satellite
    put.append(int(data[1]))
    get.append(int(data[2]))
    get_audit.append(int(data[3]))
    get_repair.append(int(data[4]))
    put_repair.append(int(data[5]))
    
    usd_get.append((20 / (1000.00**4)) * get[-1])
    usd_get_audit.append((10 / (1000.00**4)) * get_audit[-1])
    usd_get_repair.append((10 / (1000.00**4)) * get_repair[-1])

    if len(sys.argv) != 3:   
        disk.append(int(data[6]))
        usd_disk.append((1.5 / (1000.00**4)) * (max(disk[-1] - (put[-1] + put_repair[-1]), 0) + disk[-1]) / 2)
    else:
        disk.append(0)
        usd_disk.append(0)

    sums.append(put[-1] + get[-1] + get_audit[-1] + get_repair[-1] + put_repair[-1])
    
    usd_sum.append(usd_get[-1] + usd_get_audit[-1] + usd_get_repair[-1] + usd_disk[-1])

sum_total = put_total + get_total + get_audit_total + get_repair_total + put_repair_total

usd_get_total = (20 / (1000.00**4)) * get_total
usd_get_audit_total = (10 / (1000.00**4)) * get_audit_total
usd_get_repair_total = (10 / (1000.00**4)) * get_repair_total

disk_min_est = max(disk_total - (put_total + put_repair_total), 0)
disk_est = (disk_min_est + disk_total) / 2
usd_disk_total = (1.5 / (1000.00**4)) * disk_est

usd_sum_total = usd_get_total + usd_get_audit_total + usd_get_repair_total + usd_disk_total


print("\n{}".format(mdate.strftime('%B %Y')))

print("\t\t\tType\t\tDisk\t   Bandwidth\t\tPayout")
print("Upload\t\t\tIngress\t\t\t{}\t    -not paid-".format(formatSize(put_total)))
print("Upload Repair\t\tIngress\t\t\t{}\t    -not paid-".format(formatSize(put_repair_total)))
print("Download\t\tEgress\t\t\t{}\t{:10.2f} USD".format(formatSize(get_total), usd_get_total))
print("Download Repair\t\tEgress\t\t\t{}\t{:10.2f} USD".format(formatSize(get_repair_total), usd_get_repair_total))
print("Download Audit\t\tEgress\t\t\t{}\t{:10.2f} USD".format(formatSize(get_audit_total), usd_get_audit_total))
if len(sys.argv) == 3:
    print("_______________________________________________________________________________+\n")
    print("Total\t\t\t\t\t\t{}\t{:10.2f} USD".format(formatSize(sum_total), usd_sum_total))
else:
    print("Disk Average (Estimate)\tStorage\t{}\t\t\t{:10.2f} USD".format(formatSize(disk_est), usd_disk_total))
    print("_______________________________________________________________________________+\n")
    print("Total\t\t\t\t{}\t{}\t{:10.2f} USD".format(formatSize(disk_est), formatSize(sum_total), usd_sum_total))

print("\nPayout and escrow by satellite:")
print("Satellite\tType\t  Month 1-3\t  Month 4-6\t  Month 7-9\t  Month 10+")
for i in range(len(usd_sum)):
    print("{:9d}\tPayout\t{:7.4f} USD\t{:7.4f} USD\t{:7.4f} USD\t{:7.4f} USD".format(i+1,usd_sum[i]*.25,usd_sum[i]*.5,usd_sum[i]*.75,usd_sum[i]))
    print("{:9d}\tEscrow\t{:7.4f} USD\t{:7.4f} USD\t{:7.4f} USD\t{:7.4f} USD\n".format(i+1,usd_sum[i]*.75,usd_sum[i]*.5,usd_sum[i]*.25,0))

if len(sys.argv) == 3:
    print("Note: Only bandwidth is included when month parameter is used. Data stored can't be estimated for historic months.\n")
