#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on June 01 7:36 PM 2023
Created in PyCharm
Created as Misc/hydrogen_energy_levels

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt


def main():
    ns_dis = np.arange(1, 7)
    es_dis = bound_energy(ns_dis)
    ns_cont = np.linspace(1, 7, 500)
    es_cont = bound_energy(ns_cont)
    # plt.grid()
    plt.figure(figsize=(6, 3), dpi=144)
    plt.axhline(0, color='black')
    plt.plot(ns_cont, es_cont, color='red', alpha=0.4, label=r'$-13.6 eV / n^2$')
    plt.scatter(ns_dis, es_dis, marker='_', s=1000, lw=3)
    plt.xlabel('n')
    plt.ylabel('Energy (eV)')
    plt.title('Hydrogen Energy Levels')
    plt.legend()
    plt.tight_layout()
    plt.show()

    print('donzo')


def bound_energy(n):
    return -13.6 / n**2


if __name__ == '__main__':
    main()
