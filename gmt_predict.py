#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 14 12:35 AM 2022
Created in PyCharm
Created as QGP_Scripts/gmt_predict

@author: Dylan Neff, Dyn04
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit as cf

from datetime import datetime as dt


def main():
    path = 'C:/Users/Dyn04/Downloads/gmt.txt'
    times = []
    seconds = []
    pressures = []
    with open(path, 'r') as file:
        lines = file.readlines()
        for line in lines[1:]:
            line = line.strip().split()
            if len(line) == 3:
                date = line[0]
                time = line[1]
                pres = line[2]
                times.append(dt.strptime(f'{date} {time}', '%Y-%m-%d %H:%M:%S'))
                seconds.append(float(times[-1].timestamp()))
                print(seconds[-1])
                pressures.append(float(pres))

    times, seconds, pressures = np.array(times), np.array(seconds), np.array(pressures)
    plt.plot(times, pressures)
    print(list(zip(seconds, pressures)))
    popt, pcov = cf(lin, seconds, pressures)
    plt.plot(times, lin(seconds, *popt), color='red')
    down_time = (50 - popt[1]) / popt[0]
    print(down_time)
    print(dt.fromtimestamp(down_time))
    plt.show()

    print('donzo')


def lin(x, a, b):
    return a * x + b


if __name__ == '__main__':
    main()
