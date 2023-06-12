#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 20 10:32 PM 2023
Created in PyCharm
Created as Misc/grid_maker.py

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt


def main():
    """ A la chat-gpt"""
    # Set the spacing between grid lines (in units of the axes)
    x_spacing = 0.5
    y_spacing = 0.5

    # Set up the plot and axes
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=144)
    ax.set_aspect('equal')
    n_lines_x, n_lines_y = 50, 120
    line_width = 0.5
    ax.set_xlim(0, n_lines_y)
    ax.set_ylim(0, n_lines_x)

    # Create grid lines
    # x_ticks = ax.get_xticks()
    # y_ticks = ax.get_yticks()
    # x_grid = [(x_tick + x_spacing / 2) for x_tick in x_ticks for i in range(int(1 / x_spacing))]
    # y_grid = [(y_tick + y_spacing / 2) for y_tick in y_ticks for i in range(int(1 / y_spacing))]

    # Plot the grid lines
    for x in range(n_lines_x):
        ax.axhline(x, color='black', linewidth=line_width)
    for y in range(n_lines_y):
        ax.axvline(y, color='black', linewidth=line_width)

    # Show the plot
    plt.show()
    print('donzo')


if __name__ == '__main__':
    main()
