#!/usr/bin/python3

"""Show the boost status"""

import getopt
import time
import sys

import tabulate

import run_zappi
import mec.zp
import mec.power_meter
import csv
import os

# This needs to have debugging disabled.

FIELD_NAMES = {'gep': 'Generation (kWh)',
               'gen': 'Generated Negative (kWh)',
               'h1d': 'Zappi Charged Total (kWh)',
               'h1b': 'Zappi imported (kWh)',
               'imp': 'Imported (kWh)',
               'exp': 'Exported (kWh)'}

class Day():

    # Attributes
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    MONTH_NAMES = ['January', 
                   'February', 
                   'March', 
                   'April', 
                   'May', 
                   'June', 
                   'July', 
                   'August', 
                   'September', 
                   'October', 
                   'November', 
                   'December']

    #
    def DaysInMonth(month, year):
        """This method returns the number of days in a certain month (leap years supported)"""        
        if month == 2:
            if (year % 4) == 0:
                if (year % 100) == 0:
                    if (year % 400) == 0:
                        return 29
                    else:
                        return 28
                else:
                    return 29
            else:
                return 28
        else:
            return Day.month_days[month - 1]

    def __init__(self, year, month, day):
        self.tm_year = year
        self.tm_mon = month
        self.tm_mday = day
        
    def __str__(self):
        return '{} {} {}'.format(self.tm_mday, Day.MONTH_NAMES[self.tm_mon - 1], self.tm_year)

show_headers = True

def main():
    """Main"""
    global show_headers

    # Array of possible arguments
    args = ['per-minute', 'totals', 'day=', 'month=', 'year=', 'show-month', 'output-csv', 'start-day=', 'start-month=', 'start-year=']
    try:
        opts, args = getopt.getopt(sys.argv[1:], '', args)
    except getopt.GetoptError:
        print('Unknown options')
        print(args)
        sys.exit(2)

    # Default settings
    hourly = True
    totals = False
    show_month = False
    output_csv = False

    # Set default day, and start_day for show_month
    today = time.localtime()
    start_day = Day(today.tm_year, today.tm_mon, 1)
    day = Day(today.tm_year, today.tm_mon, today.tm_mday)

    # Check arguments
    for opt, value in opts:
        if opt == '--per-minute':
            hourly = False
        if opt == '--totals':
            totals = True
        if opt == '--day':
            day.tm_mday = int(value)
        if opt == '--month':
            day.tm_mon = int(value)
        if opt == '--year':
            day.tm_year = int(value)
        if opt == '--show-month':
            show_month = True
        if opt == '--output-csv':
            output_csv = True
        if opt == '--start-day':
            start_day.tm_mday = int(value)
        if opt == '--start-month':
            start_day.tm_mon = int(value)
        if opt == '--start-year':
            start_day.tm_year = int(value)
        
    # Check if start date is before end date, otherwise edit it such that it is
    if start_day.tm_year > day.tm_year:
        start_day.tm_year = day.tm_year
        start_day.tm_mon = day.tm_mon
    elif start_day.tm_year == day.tm_year and start_day.tm_mon > day.tm_mon:
        start_day.tm_mon = day.tm_mon
    elif start_day.tm_year == day.tm_year and start_day.tm_mon == day.tm_mon and start_day.tm_mday > day.tm_mday:
        start_day.tm_mday = day.tm_mday
      
    # Print start and end dates as a check
    if output_csv:
        print("Start Date:" + str(start_day))
        print("End Date:" + str(day))
        input("Press Enter to continue...")

    # Load config file
    config = run_zappi.load_config(debug=False)

    # Connect to MyEnergiServer
    server_conn = mec.zp.MyEnergiHost(config['username'], config['password'])
    server_conn.refresh()
    

    # Iterate through all available Zappi V2.
    for zappi in server_conn.state.zappi_list():
        zid = zappi.sno

        show_headers = True
        
        # Create CSV file if applicable
        if output_csv:
            
            # Create output folder if it does not already exist
            if not os.path.exists('Output'):
                os.mkdir('Output')            
            
            csvfile = open('Output/MyEnergiData' + '{:04d}'.format(today.tm_year) +
                                                 '{:02d}'.format(today.tm_mon) + 
                                                 '{:02d}'.format(today.tm_mday) + '_' +
                                                 '{:02d}'.format(today.tm_hour) + 
                                                 '{:02d}'.format(today.tm_min) + 
                                                 '{:02d}'.format(today.tm_sec) + '.csv', 'w', newline='')
            
            # Fields used in the outputted CSV file
            fieldnames = ['Time', 
                          'imp', 
                          'exp', 
                          #'gen', 
                          'gep', 
                          'h1d', 
                          #'h1b', 
                          #'pect1', 'nect1', 'pect2', 'nect2', 'pect3', 'nect3'
                          ]
            fieldnames_readable = fieldnames.copy()
            for key in range(0, len(fieldnames)):     
                if fieldnames_readable[key] in FIELD_NAMES:                   
                    fieldnames_readable[key] = FIELD_NAMES[fieldnames_readable[key]]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames_readable, dialect='excel', restval='', quoting=int(csv.QUOTE_NONNUMERIC), delimiter=';')
            writer.writeheader()

        # Iterate through long term data from start date to end date
        if show_month:             
            all_data = []
            for yr in range(start_day.tm_year, day.tm_year + 1):
                morange = range(1, 12 + 1)
                if (yr == start_day.tm_year):
                    if (yr < day.tm_year):
                        morange = range(start_day.tm_mon, 12 + 1)
                    else:
                        morange = range(start_day.tm_mon, day.tm_mon + 1)
                elif (yr == day.tm_year):
                    morange = range(1, day.tm_mon + 1)
                for mo in morange:
                    dyrange = range(1, Day.DaysInMonth(mo, yr) + 1)
                    if (yr == start_day.tm_year and mo == start_day.tm_mon):
                        if (yr < day.tm_year or mo < day.tm_mon):
                            dyrange = range(start_day.tm_mday, Day.DaysInMonth(mo, yr) + 1)
                        else:
                            dyrange = range(start_day.tm_mday, day.tm_mday + 1)
                    elif (yr == day.tm_year and mo == day.tm_mon):
                        dyrange = range(1, day.tm_mday + 1)
                    
                    for dom in dyrange:
                        queryday = Day(yr, mo, dom)
                        print('Date: {}'.format(str(queryday)))
                        
                        (headers, _, totals, pm_totals) = load_day(server_conn, zid, queryday, hourly, totals, output_csv=output_csv)
                        if output_csv:
                            data_row = {key: value for key, value in pm_totals.items()
                                    if key in fieldnames}
                            for key in fieldnames:     
                                if key in FIELD_NAMES:                   
                                    data_row[FIELD_NAMES[key]] = data_row.pop(key)
                            data_row['Time'] = '{}-{}-{}'.format(queryday.tm_mday, queryday.tm_mon, queryday.tm_year);
                            writer.writerow(data_row)
                        all_data.append(totals)
            if not output_csv:
                print(tabulate.tabulate(all_data, headers=headers))
        else:
            load_day(server_conn, zid, day, hourly, totals)
            
        if output_csv:
            csvfile.close()

def load_day(server_conn, zid, day, hourly, totals, output_csv=False):

    global show_headers

    if hourly:
        res = server_conn.get_hour_data(zid, day=day)
        prev_sample_time = - 60 * 60
    else:
        res = server_conn.get_minute_data(zid, day=day)
        prev_sample_time = -60
    
    headers = ['imp', 'exp', 'gen', 'gep', 'h1d', 'h1b', 'pect1', 'nect1', 'pect2', 'nect2', 'pect3', 'nect3']
    table_headers = ['Time', 'Duration']
    data = []
    pm_totals = {}
    for key in headers:
        pm_totals[key] = mec.power_meter.PowerMeter(show_kWh_in_Data=False)
        pm_totals[key].add_value(0, prev_sample_time)
        if key in FIELD_NAMES:
            table_headers.append(FIELD_NAMES[key])
        else:
            table_headers.append(key)
    for rec in res:
        row = []
        hour = 0
        minute = 0
        volts = 1

        if 'imp' in rec and 'nect1' in rec and rec['imp'] == rec['nect1']:
            del rec['nect1']
        if 'exp' in rec and 'pect1' in rec and rec['exp'] == rec['pect1']:
            del rec['pect1']
        if 'hr' in rec:
            hour = rec['hr']
            del rec['hr']
        if 'min' in rec:
            minute = rec['min']
            del rec['min']

        sample_time = ((hour * 60) + minute) * 60

        for key in ['dow', 'yr', 'mon', 'dom']:
            del rec[key]

        if 'v1' in rec:
            volts = rec['v1'] / 10
        for key in ['v1', 'frq']:
            if key in rec:
                del rec[key]

        row.append('{:02}:{:02}'.format(hour, minute))
        row.append(sample_time - prev_sample_time)

        for key in headers:
            if key in rec:
                value = rec[key]
                if hourly:
                    watts = value / (60 * 60)
                else:
                    watts = value / volts * 4
                row.append(int(watts))
                del rec[key]
            else:
                watts = 0
                row.append(None)
            pm_totals[key].add_value(watts, sample_time)
        prev_sample_time = sample_time

        if rec:
            print(rec)
        data.append(row)
    num_records = len(data)
    if not output_csv:
        print('There are {} records'.format(num_records))
    if totals:
        data = []
    row = ['Totals', None]
    for key in headers:
        row.append(pm_totals[key])
    data.append(row)

    if show_headers:
        if not output_csv:
            print(tabulate.tabulate(data, headers=table_headers))
        show_headers = False
    elif not output_csv:
            print(tabulate.tabulate(data))
    return (table_headers, data, row, pm_totals)

if __name__ == '__main__':
    main()
