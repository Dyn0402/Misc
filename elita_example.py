#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on January 27 8:34 PM 2025
Created in PyCharm
Created as Misc/elita_example.py

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt


def main():
    array_1d = np.random.random(size=10000) * 100
    n_bins = 100
    hist_range = (0, 100)
    cut = 20

    array_1d_cut = array_1d[array_1d > cut]

    fig, ax = plt.subplots()
    ax.hist(array_1d, bins=n_bins, range=hist_range, histtype='step', label='All Data')
    ax.hist(array_1d_cut, bins=n_bins, range=hist_range, label=f'Data > {cut}')
    ax.set_xlabel('Value')
    ax.set_ylabel('Count')
    ax.set_title('Random Data Histogram')
    ax.legend()
    fig.tight_layout()
    plt.show()


    print('donzo')


if __name__ == '__main__':
    main()
