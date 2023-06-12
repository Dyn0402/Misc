#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on May 12 12:01 PM 2023
Created in PyCharm
Created as Misc/hotdog_plot

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt


def main():
    plot_inv_exp()
    plot_exp_decay()
    plt.show()

    print('donzo')


def plot_inv_exp():
    a, b = 3, 0.8
    ts = np.linspace(0, 5, 100)
    plt.figure(figsize=(5, 4))
    plt.axhline(0, color='black')
    plt.axvline(0, color='black')
    plt.axhline(a, color='red', ls=':')
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.plot(ts, inv_exp(ts, a, b))
    plt.plot([0, 1 / b], [inv_exp(1 / b, a, b), inv_exp(1 / b, a, b)], color='blue', alpha=0.5)
    plt.plot([1 / b, 1 / b], [0, inv_exp(1 / b, a, b)], color='blue', alpha=0.5)
    plt.tight_layout()


def plot_exp_decay():
    a, b = 3, 0.8
    ts = np.linspace(0, 5, 100)
    plt.figure(figsize=(5, 4))
    plt.axhline(0, color='black')
    plt.axvline(0, color='black')
    plt.axhline(a, color='red', ls=':')
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.plot(ts, exp_decay(ts, a, b))
    plt.plot([0, 1 / b], [exp_decay(1 / b, a, b), exp_decay(1 / b, a, b)], color='blue', alpha=0.5)
    plt.plot([1 / b, 1 / b], [0, exp_decay(1 / b, a, b)], color='blue', alpha=0.5)
    plt.tight_layout()


def inv_exp(t, a, b):
    return a * (1 - np.exp(-b * t))


def exp_decay(t, a, b):
    return a * np.exp(-b * t)


if __name__ == '__main__':
    main()
