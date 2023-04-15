#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on September 10 5:02 PM 2022
Created in PyCharm
Created as Misc/wedding_overlap_prob

@author: Dylan Neff, Dyn04
"""

import numpy as np
import matplotlib.pyplot as plt


def main():
    n_weddings = np.arange(1, 53, 1)
    overlap_probs = np.array([overlap_prob(n_wedding) for n_wedding in n_weddings])
    fig, ax = plt.subplots()
    ax.plot(n_weddings, overlap_probs)
    # ax.axhline(0, color='black')
    # ax.vlines(12, ymin=ax.get_ylim()[0], ymax=overlap_prob(12), color='red', ls='--')
    # ax.hlines(overlap_prob(12), xmin=ax.get_xlim()[0], xmax=12, color='red', ls='--')
    ax.set_xlabel('Number of Wedding Weekends in a Year')
    ax.set_ylabel('Probability of No Wedding Weekends Overlapping')
    ax.grid()
    plt.show()
    print(overlap_prob(12))
    print('donzo')


def overlap_prob(n_weddings):
    """
    Calculate probability of any uncorrelated wedding weekends overlapping in a year.
    :param n_weddings: Number of weddings in a year
    :return:
    """
    year_weeks = 52
    numerator_array = year_weeks + 1 - np.arange(1, n_weddings + 1, 1)
    return np.product(numerator_array / year_weeks)


if __name__ == '__main__':
    main()
