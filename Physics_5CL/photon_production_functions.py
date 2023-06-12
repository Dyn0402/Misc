#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on June 11 4:49 PM 2023
Created in PyCharm
Created as Misc/photon_production_functions

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm

from matplotlib.colors import LinearSegmentedColormap


def main():
    mu_discrete, mu_led = 600, 450
    sigma_discrete, sigma_led = 0.1, 10
    blackbody_temp = 3000

    wavelengths = np.linspace(300, 800, 10000)
    discrete_pdf = norm(mu_discrete, sigma_discrete).pdf
    led_pdf = norm(mu_led, sigma_led).pdf

    discrete_pdf = discrete_pdf(wavelengths)
    discrete_pdf /= max(discrete_pdf)
    led_pdf = led_pdf(wavelengths)
    led_pdf /= max(led_pdf)
    blackbody_pdf = blackbody_spectrum(wavelengths, blackbody_temp)
    blackbody_pdf /= max(blackbody_pdf)

    plt.plot(wavelengths, discrete_pdf, label='Discrete')
    plt.plot(wavelengths, led_pdf, label='LED')
    plt.plot(wavelengths, blackbody_pdf, label='Blackbody')
    plt.xlabel('Photon Wavelength (nm)')
    plt.ylabel('Photon Intensity')
    plt.legend()

    plt.show()
    print('donzo')


def blackbody_spectrum(wavelength, temperature):
    """
    Function to calculate the blackbody spectrum (written by chat-gpt)
    :param wavelength: nm
    :param temperature: K
    :return:
    """
    # Constants
    h = 6.62607015e-34  # Planck's constant (J*s)
    c = 2.99792458e8  # Speed of light (m/s)
    k = 1.380649e-23  # Boltzmann constant (J/K)

    # Convert wavelength to meters
    wavelength_m = wavelength * 1e-9

    # Calculate the spectral radiance using Planck's law
    numerator = 2 * h * c**2
    denominator = wavelength_m**5 * (np.exp((h * c) / (wavelength_m * k * temperature)) - 1)
    spectral_radiance = numerator / denominator

    return spectral_radiance


if __name__ == '__main__':
    main()
