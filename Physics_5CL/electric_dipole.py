#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on May 19 11:54 AM 2023
Created in PyCharm
Created as Misc/electric_dipole

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt

k = 8.988e9  # N * m^2 / C^2


def main():
    e_charge = 1.602176634e-19  # C of charge per electron
    q1, q2 = 1 * e_charge, -1 * e_charge  # C
    volt_distance = 1  # V to define distance scale
    r_scale = k * e_charge / volt_distance
    x_q1, x_q2 = np.array([-1, 0]) * r_scale, np.array([1, 0]) * r_scale
    x_obs = np.array([-1, -1]) * r_scale
    obs_pot = get_potential(x_obs, q1, x_q1, q2, x_q2)
    print(f'Potential at {x_obs}: {obs_pot}V')

    x_obs_min, x_obs_max = -150, 150
    x_obs_path = np.linspace(x_obs_min, x_obs_max, 1000) * r_scale
    y_fix = -1 * r_scale
    vs = []
    for xi in x_obs_path:
        vs.append(get_potential(np.array([xi, y_fix]), q1, x_q1, q2, x_q2))

    plt.figure()
    plt.plot(x_obs_path, vs)
    plt.xlabel('x_pos of dipole voltage measurement')
    plt.ylabel('Voltage')

    measurement_separation = 100 * r_scale
    v_diffs, v_lefts, v_rights = [], [], []
    for xi in x_obs_path:
        v_left = get_potential(np.array([xi - measurement_separation / 2, y_fix]), q1, x_q1, q2, x_q2)
        v_right = get_potential(np.array([xi + measurement_separation / 2, y_fix]), q1, x_q1, q2, x_q2)
        v_lefts.append(v_left)
        v_rights.append(v_right)
        v_diffs.append(v_left - v_right)

    plt.figure()
    plt.axhline(0, color='black', alpha=0.5)
    plt.axvline(0, color='black', alpha=0.5)
    plt.plot(x_obs_path, v_lefts, label='Left')
    plt.plot(x_obs_path, v_rights, label='Right')
    plt.plot(x_obs_path, v_diffs, label='Left - Right')
    plt.xlabel('Center of leads')
    plt.ylabel('Voltage')
    plt.legend()
    plt.tight_layout()

    plt.show()

    print('donzo')


def get_potential(x_obs, q1, x_q1, q2, x_q2):
    return point_charge_potential(x_obs, x_q1, q1) + point_charge_potential(x_obs, x_q2, q2)


def point_charge_potential(x_obs, x_dipole, q_dipole):
    return k * q_dipole / (np.linalg.norm(x_obs - x_dipole))


if __name__ == '__main__':
    main()
