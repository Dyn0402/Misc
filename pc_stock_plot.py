#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on November 21 10:45 AM 2020
Created in PyCharm
Created as Misc/pc_stock_plot

@author: Dylan Neff, Dylan
"""


import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta


def main():
    path = 'C:/Users/Dylan/Desktop/ryzen_stock.txt'
    item = 'Ryzen 5 5600X'
    in_mode = 'lines'
    # path = 'C:/Users/Dylan/Desktop/msi_tom_stock.txt'
    # item = 'MAG X570 TOMAHAWK WIFI'
    # in_mode = 'tabs'
    stock_data = read_stock_file(path, mode=in_mode)
    stock_data = filter_stock_items(stock_data, item)
    for date, item in zip(stock_data[0], stock_data[1]):
        print(f'{date}\t{item}')
    stock_periods = pair_stock_dates(stock_data)
    for vendor, periods in stock_periods.items():
        print(f'Vendor {vendor}:')
        for period in periods:
            print(f'{period[0]} to {period[1]}')
    plot_periods(stock_periods)
    print('donzo')


def read_stock_file(path, mode='lines'):
    stock_data = [[], []]

    with open(path, 'r') as file:
        lines = file.readlines()

        if mode.lower() == 'lines':
            line_num = 1
            for line in lines:
                if line_num % 2:
                    line = line.strip().replace(' EST', '')
                    dt_format = '%b %d %Y - %I:%M %p'
                    dt = datetime.strptime(line, dt_format)
                    dt += timedelta(seconds=30) - timedelta(hours=3)
                    stock_data[0].append(dt)
                else:
                    line = line.strip().split(' - ')
                    item_dict = {'vendor': line[0]}
                    if ' in stock' in line[1].lower():
                        item = line[1][:line[1].lower().find(' in stock')]
                        item_dict.update({'item': item, 'available': True})
                    elif ' preorder' in line[1].lower():
                        item = line[1][:line[1].lower().find(' preorder')]
                        item_dict.update({'item': item, 'available': True})
                    elif ' out of stock' in line[1].lower():
                        item = line[1][:line[1].lower().find(' out of stock')]
                        item_dict.update({'item': item, 'available': False})
                    else:
                        print(f"Can't parse item availability: {line}")
                    stock_data[1].append(item_dict)
                line_num += 1

        elif mode.lower() == 'tabs':
            for line in lines:
                line = line.strip().split('\t')

                print(line)
                date_str = line[0].replace(' EST', '')
                print(date_str)
                dt_format = '%b %d %Y - %I:%M %p'
                dt = datetime.strptime(date_str, dt_format)
                dt += timedelta(seconds=30) - timedelta(hours=3)
                stock_data[0].append(dt)

                line = line[1].strip().split(' - ')
                item_dict = {'vendor': line[0]}
                if ' in stock' in line[1].lower():
                    item = line[1][:line[1].lower().find(' in stock')]
                    item_dict.update({'item': item, 'available': True})
                elif ' preorder' in line[1].lower():
                    item = line[1][:line[1].lower().find(' preorder')]
                    item_dict.update({'item': item, 'available': True})
                elif ' out of stock' in line[1].lower():
                    item = line[1][:line[1].lower().find(' out of stock')]
                    item_dict.update({'item': item, 'available': False})
                else:
                    print(f"Can't parse item availability: {line}")
                stock_data[1].append(item_dict)

    return stock_data


def filter_stock_items(stock_data, item_filter):
    filtered_stock_items = [[], []]
    item_filter = item_filter.lower()
    for date, item in zip(stock_data[0], stock_data[1]):
        if item_filter in item['item'].lower():
            filtered_stock_items[0].append(date)
            filtered_stock_items[1].append(item)

    return filtered_stock_items


def pair_stock_dates(stock_data):
    stock_periods = {}
    vendors = list(set([item['vendor'] for item in stock_data[1]]))
    print(vendors)
    for vendor in vendors:
        stock_periods.update({vendor: []})
        start = None
        for date, item in sorted(zip(stock_data[0], stock_data[1])):
            if item['vendor'] == vendor:
                if start:
                    if item['available']:
                        print(f'Double available: {date}\t\t{item}')
                    else:
                        stock_periods[vendor].append([start, date])
                        start = None
                else:
                    if item['available']:
                        start = date
                    else:
                        print(f'Starting unavailable or double unavailable: {date}\t\t{item}')

    return stock_periods


def plot_periods(stock_periods):
    durations = {}
    for vendor, periods in stock_periods.items():
        durations.update({vendor: [[], [], [], []]})
        for period in periods:
            durations[vendor][0].append(period[0])
            durations[vendor][1].append(timedelta(seconds=30))
            durations[vendor][2].append((period[1] - period[0]).seconds / 60)
            durations[vendor][3].append(1)
        plt.errorbar(durations[vendor][0], durations[vendor][2], durations[vendor][3], durations[vendor][1],  'o--',
                     label=vendor)
        plt.gcf().autofmt_xdate()

    plt.axhline(0, color='black')
    plt.ylabel('Time Available (Minutes)')
    plt.legend()
    plt.show()


if __name__ == '__main__':
    main()
