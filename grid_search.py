#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on May 14 3:18 PM 2020
Created in PyCharm
Created as Misc/grid_search.py

@author: Dylan Neff, dylan
"""


from scipy.optimize import curve_fit as cf
import matplotlib.pyplot as plt
import numpy as np


def main():
    streets_away = [0]
    streets_to_check = [0]
    check_time = [0]
    walk_time = [0]
    lines = 0
    drive_time_per_street = 15  # s
    walk_time_per_street = 90  # s
    for i in range(7):
        print(f'{streets_away[-1]} streets away, {streets_to_check[-1]} streets to check, '
              f'{streets_to_check[-1] * drive_time_per_street}s check time')
        streets_to_check.append(streets_to_check[-1] + 4 * new_lines(lines))
        check_time.append(streets_to_check[-1] * drive_time_per_street / 2 / 60)  # in minutes
        streets_away.append(streets_away[-1] + 1)
        walk_time.append(streets_away[-1] * walk_time_per_street / 60)  # in minutes
        lines += 2
    popt, pcov = cf(poly_2, streets_away, streets_to_check)
    print(popt)
    popt, pcov = cf(poly_2, streets_away, check_time)
    print(popt)
    fig, ax1 = plt.subplots()
    ax1.plot(streets_away[1:], check_time[1:], 'bo')
    x_plot = np.linspace(1, 7, 1000)
    ax1.plot(x_plot, poly_2(x_plot, *popt), 'r', label='Average Time to Find Car')
    ax1.set_xlabel('Distance of Car from Apartment (Blocks)')
    ax1.set_ylabel('Time to Car (Minutes)')
    ax1.plot(streets_away[1:], walk_time[1:], 'g', label='Time to Walk to Car')
    plt.title('Average Time to Find Car Via Grid Search')
    ax1.grid()
    ax1.legend()
    plt.show()
    print('donzo')


def poly_2(x, a, b, c):
    return a + b * x + c * x**2


def new_lines(old_lines):
    return 2 * old_lines + 3


if __name__ == '__main__':
    main()

