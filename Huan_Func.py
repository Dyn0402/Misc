#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on September 07 6:32 PM 2020
Created in PyCharm
Created as Misc/Huan_Func.py

@author: Dylan Neff, Dyn04
"""

import numpy as np
import matplotlib.pyplot as plt


def main():
    amp = [1.9, 2, 2.1]
    x0 = [-2, 2, 0]
    curv = [0.5, 2, 50]
    x = np.linspace(-10, 10, 1000)
    for i in range(len(amp)):
        plt.plot(x, huan_func(x, amp[i], curv[i], x0[i]), label=f'{amp[i]} / (1 + exp(-{curv[i]} * (x - {x0[i]})))')
    plt.legend()
    plt.xlabel('x')
    plt.grid()
    plt.show()
    print('donzo')


def huan_func(x, amp, curv, x0):
    return amp / (1 + np.exp(-curv * (x - x0)))


if __name__ == '__main__':
    main()