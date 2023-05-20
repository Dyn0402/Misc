#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on May 20 12:23 AM 2023
Created in PyCharm
Created as Misc/emg_sim.py

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt

import multiprocessing
from tqdm import tqdm


k = 8.988e9  # N * m^2 / C^2


def main():
    arm_len = 25.  # cm
    pos_lead_z = 12.  # cm
    neg_lead_z = 13.  # cm
    muscle_depth = 2.  # cm
    muscle_radius = 1.  # cm
    muscle_charge_sep = 0.01  # cm

    n_rings_z = 500
    n_points_ring = 50

    q_out_rest, q_in_rest, q_out_ap, q_in_ap = +1e-10, -1e-10, -1e-10, +1e-10  # C Total charge of rings
    n_points_ap = 20
    v_ap = 10000  # cm/s

    processes = 10

    dt = arm_len / n_rings_z / v_ap  # s

    pos_lead_pos, neg_lead_pos = np.array([0, 0, pos_lead_z]), np.array([0, 0, neg_lead_z])
    z_rings = np.linspace(0, arm_len, n_rings_z)

    t = -2 * dt
    ts, pos_lead_pots, neg_lead_pots = [], [], []

    pool = multiprocessing.Pool(processes=processes)
    results = []

    ts = np.arange(t, arm_len / v_ap)

    args = [v_ap, n_points_ap, arm_len, n_rings_z, z_rings, n_points_ring, muscle_radius,  muscle_charge_sep,
              muscle_depth, q_out_ap, q_out_rest, q_in_ap, q_in_rest, pos_lead_pos, neg_lead_pos]
    with tqdm(total=len(ts)) as pbar:
        for result in pool.imap(calc_ring, ts, args * len(ts)):
            results.append(result)
            pbar.update(1)

    while t <= arm_len / v_ap:

        pos_lead_pot, neg_lead_pot = 0, 0
        z_ap_max = t * v_ap
        z_ap_min = z_ap_max - n_points_ap * arm_len / n_rings_z
        for ring_z in z_rings:
            for angle in np.linspace(0, 2*np.pi, n_points_ring):
                out_radius = muscle_radius + muscle_charge_sep / 2
                out_x = out_radius * np.cos(angle)
                out_y = -muscle_depth + out_radius * np.sin(angle)
                out_point_pos = np.array([out_x, out_y, ring_z])
                q_out = q_out_ap if z_ap_min < ring_z <= z_ap_max else q_out_rest
                out_point_q = q_out / n_points_ring

                in_radius = muscle_radius - muscle_charge_sep / 2
                in_x = in_radius * np.cos(angle)
                in_y = -muscle_depth + in_radius * np.sin(angle)
                in_point_pos = np.array([in_x, in_y, ring_z])
                q_in = q_in_ap if z_ap_min < ring_z <= z_ap_max else q_in_rest
                in_point_q = q_in / n_points_ring

                pos_lead_pot += calc_point_pot_cm(pos_lead_pos, out_point_pos, out_point_q)
                pos_lead_pot += calc_point_pot_cm(pos_lead_pos, in_point_pos, in_point_q)

                neg_lead_pot += calc_point_pot_cm(neg_lead_pos, out_point_pos, out_point_q)
                neg_lead_pot += calc_point_pot_cm(neg_lead_pos, in_point_pos, in_point_q)
        ts.append(t)
        pos_lead_pots.append(pos_lead_pot)
        neg_lead_pots.append(neg_lead_pot)
        print(f't={t:.6f}s')
        t += dt

    plt.figure()
    plt.grid()
    plt.plot(ts, pos_lead_pots, label='Positive Lead')
    plt.plot(ts, neg_lead_pots, label='Negative Lead')
    plt.plot(ts, np.array(pos_lead_pots) - np.array(neg_lead_pots), label='Difference')
    plt.legend()
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.tight_layout()

    plt.figure()
    plt.grid()
    plt.plot(ts, pos_lead_pots, label='Positive Lead')
    plt.plot(ts, neg_lead_pots, label='Negative Lead')
    plt.legend()
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.tight_layout()

    plt.figure()
    plt.grid()
    plt.plot(ts, np.array(pos_lead_pots) - np.array(neg_lead_pots), label='Difference')
    plt.legend()
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.tight_layout()

    plt.show()

    print('donzo')


def calc_ring(t, v_ap, n_points_ap, arm_len, n_rings_z, z_rings, n_points_ring, muscle_radius,  muscle_charge_sep,
              muscle_depth, q_out_ap, q_out_rest, q_in_ap, q_in_rest, pos_lead_pos, neg_lead_pos):
    pos_lead_pot, neg_lead_pot = 0, 0
    z_ap_max = t * v_ap
    z_ap_min = z_ap_max - n_points_ap * arm_len / n_rings_z
    for ring_z in z_rings:
        for angle in np.linspace(0, 2 * np.pi, n_points_ring):
            out_radius = muscle_radius + muscle_charge_sep / 2
            out_x = out_radius * np.cos(angle)
            out_y = -muscle_depth + out_radius * np.sin(angle)
            out_point_pos = np.array([out_x, out_y, ring_z])
            q_out = q_out_ap if z_ap_min < ring_z <= z_ap_max else q_out_rest
            out_point_q = q_out / n_points_ring

            in_radius = muscle_radius - muscle_charge_sep / 2
            in_x = in_radius * np.cos(angle)
            in_y = -muscle_depth + in_radius * np.sin(angle)
            in_point_pos = np.array([in_x, in_y, ring_z])
            q_in = q_in_ap if z_ap_min < ring_z <= z_ap_max else q_in_rest
            in_point_q = q_in / n_points_ring

            pos_lead_pot += calc_point_pot_cm(pos_lead_pos, out_point_pos, out_point_q)
            pos_lead_pot += calc_point_pot_cm(pos_lead_pos, in_point_pos, in_point_q)

            neg_lead_pot += calc_point_pot_cm(neg_lead_pos, out_point_pos, out_point_q)
            neg_lead_pot += calc_point_pot_cm(neg_lead_pos, in_point_pos, in_point_q)

    return pos_lead_pot, neg_lead_pot


def calc_point_pot_cm(obs_pos, point_pos, point_q):
    return k * point_q / (np.linalg.norm(obs_pos - point_pos) / 100)


if __name__ == '__main__':
    main()
