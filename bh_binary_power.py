#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 01 9:47 PM 2020
Created in PyCharm
Created as Misc/bh_binary_power

@author: Dylan Neff, Dylan
"""

import matplotlib.pyplot as plt
import numpy as np

# Constants
g = 6.67e-11  # m^3 kg^-1 s^-2
c = 2.9927e8  # m s^-2
m_solar = 1.989e30  # kg


def main():
    m_chirp = 30 * m_solar / 2**(1.0/5)  # kg
    taus = np.linspace(0.00002, 7, 1000000)
    powers = power(taus, m_chirp)

    plt.plot(taus, powers, color='blue', label='Power')
    plt.axvline(6.04746, linestyle='--', color='green', label='10Hz')
    plt.axvline(0.000028, linestyle='--', color='red', label='1000Hz')
    plt.xlabel(r'$\tau = t_{coal} - t$  (seconds)')
    plt.ylabel('Power (watts)')
    plt.semilogx()
    plt.legend()
    plt.show()

    plt.plot(taus, powers, color='blue', label='Power')
    plt.axvline(6.04746, linestyle='--', color='green', label='10Hz')
    plt.axvline(0.000028, linestyle='--', color='red', label='1000Hz')
    plt.xlabel(r'$\tau = t_{coal} - t$  (seconds)')
    plt.ylabel('Power (watts)')
    plt.legend()
    plt.show()

    print('donzo')


def power(tau, m_chirp):
    p = 32.0 / 5 * c**5 / g * \
        (g * m_chirp * np.pi * 134.0 / c**3)**(10.0/3) * (1.21 * m_solar / m_chirp)**(20.0/18) * (1.0 / tau)**(5.0/4)

    return p


if __name__ == '__main__':
    main()
