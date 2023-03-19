#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on June 14 11:24 AM 2021
Created in PyCharm
Created as Misc/per_diem_calc

@author: Dylan Neff, Dyn04
"""


from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


def main():
    path = 'C:/Users/Dyn04/OneDrive/Tablet/UCLA/Research/STAR/Shifts/Run21/Reimbursement/Chase_Card.CSV'
    cap = 62  # Max price per day
    avg = 60
    data = read_data(path)
    data = fill_in_days(data)
    plot_data(data, 'Original')
    flat_data = cap_data(data.copy(), cap)
    plot_data(flat_data, 'Capped')
    buffed_data = buff_data(flat_data.copy(), avg)
    # flat_buffed_data = cap_data(buffed_data.copy(), cap)
    plot_data(buffed_data, 'Buffed')
    print_final(buffed_data)
    plt.show()
    print('donzo')


def read_data(path):
    data = {}
    with open(path, 'r') as file:
        lines = file.readlines()
        for line in lines:
            line = line.strip().split(',')
            try:
                dt = datetime.strptime(line[0], '%m/%d/%Y')
                price = -float(line[-2])
                if dt in data.keys():
                    data[dt] += price
                else:
                    data[dt] = price
            except ValueError:
                print(f'bad line: {line}')

    return data


def fill_in_days(data):
    date = min(data)
    while date < max(data):
        if date not in data:
            data[date] = 0
        date += timedelta(days=1)

    data = dict(sorted(data.items()))

    return data


def cap_data(data, cap=62):
    min_date = min(data)
    max_date = max(data)
    finished = False
    date_step = timedelta(days=1)

    while not finished:
        finished = True
        for date in data.keys():
            excess = 0
            if data[date] > cap:
                excess = data[date] - cap
                data[date] = cap
                finished = False
            if date - date_step < min_date:
                data[date + date_step] += excess
            elif date + date_step > max_date:
                data[date - date_step] += excess
            else:
                data[date - date_step] += excess / 2
                data[date + date_step] += excess / 2

    return data


def buff_data(data, avg=60, cap=62):
    pre_avg = np.mean(list(data.values()))
    corr_factor = (avg - pre_avg) / (cap - pre_avg)

    for date in data.keys():
        diff = cap - data[date]
        data[date] += diff * corr_factor

    post_avg = np.mean(list(data.values()))

    print(f'Pre_avg: {pre_avg}, post_avg: {post_avg}')

    return data


def plot_data(data, name='Spent per day'):
    print(f'{name} sum: {sum(data.values())}')
    fig, ax = plt.subplots()
    dates = data.keys()
    spent = data.values()
    ax.plot(dates, spent)
    date_fmt = mdates.DateFormatter('%m/%d')
    ax.xaxis.set_major_formatter(date_fmt)
    ax.tick_params(axis='x', labelrotation=30)
    ax.set_ylim([0, 175])
    ax.set_title(name)
    ax.grid()
    # plt.show()


def print_final(data):
    for date, spent in data.items():
        print(f'{date.strftime("%m/%d/%Y")} {spent:0.2f}')


if __name__ == '__main__':
    main()
