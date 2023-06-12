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
import matplotlib.cm as cm

from scipy.interpolate import interp1d

import multiprocessing
from tqdm import tqdm


k = 8.988e9  # N * m^2 / C^2


def main():
    # full_emg_sim()
    charged_cylinder_potential()
    print('donzo')


def full_emg_sim():
    arm_len = 30.  # cm
    arm_radius = 3  # cm
    pos_lead_z = 20.  # cm
    neg_lead_z = 10.  # cm
    muscle_depth = 1.  # cm
    muscle_radius = 0.6e-6 * 100  # cm
    muscle_charge_sep = muscle_radius / 10  # cm

    n_rings_z = 151
    # n_rings_z = 1
    n_points_ring = 50
    # Muscle ca++
    charge_time = 0.5  # s  Characteristic time to get from q_rest to q_ap
    discharge_time = 0.05  # s  Characteristic time to decay from q_ap back to q_rest
    q_out_rest, q_in_rest, q_out_ap, q_in_ap = +1e-10, 0, 0, +1e-10  # C Total charge of rings

    # Muscle action potential
    # charge_time = 0.00125  # s  Characteristic time to get from q_rest to q_ap
    # discharge_time = 0.001  # s  Characteristic time to decay from q_ap back to q_rest
    # q_out_rest, q_in_rest, q_out_ap, q_in_ap = +1e-10, -1e-10, -1e-10, +1e-10  # C Total charge of rings

    v_ap = 400  # cm/s

    plot = True
    cmap = cm.get_cmap('bwr')

    # processes = 10

    dt = arm_len / n_rings_z / v_ap  # s
    # dt = 0.001

    ap_charge_t_max = -np.log(charge_time / (discharge_time + charge_time)) * charge_time
    ap_charge_max = ap_function(ap_charge_t_max, charge_time, discharge_time)

    pos_lead_pos, neg_lead_pos = np.array([0, 0, pos_lead_z]), np.array([0, 0, neg_lead_z])
    z_rings = np.linspace(0, arm_len, n_rings_z)
    # z_rings = np.array([0.5 * arm_len])
    out_radius = muscle_radius + muscle_charge_sep / 2
    in_radius = muscle_radius - muscle_charge_sep / 2

    # t_start, t_end = -2 * dt, arm_len / v_ap
    t_start = -2 * dt
    t_end = max(discharge_time * 2, 1.5 * arm_len / v_ap)
    ts, pos_lead_pots, neg_lead_pots = [], [], []

    # pool = multiprocessing.Pool(processes=processes)
    # results = []

    ts_plot = np.arange(0, t_end, dt)

    angles = np.linspace(0, 2 * np.pi, n_points_ring)
    out_x = out_radius * np.cos(angles)
    out_y = -muscle_depth + out_radius * np.sin(angles)
    in_x = in_radius * np.cos(angles)
    in_y = -muscle_depth + in_radius * np.sin(angles)

    # args = [v_ap, n_points_ap, arm_len, n_rings_z, z_rings, n_points_ring, muscle_radius,  muscle_charge_sep,
    #           muscle_depth, q_out_ap, q_out_rest, q_in_ap, q_in_rest, pos_lead_pos, neg_lead_pos]
    # with tqdm(total=len(ts)) as pbar:
    #     for result in pool.imap(calc_ring, ts, args * len(ts)):
    #         results.append(result)
    #         pbar.update(1)

    fig, ax = plt.subplots(dpi=144)
    ax.grid()
    ax.plot(ts_plot, ap_charge(ts_plot, charge_time, discharge_time, q_out_rest, q_out_ap, ap_charge_max))
    ax.set_xlabel('Time from Action Potential (s)')
    ax.set_ylabel('Charge Outside (C)')
    fig.tight_layout()

    if plot:
        fig, axs = plt.subplots(nrows=2, figsize=(10, 5), dpi=144)
        plot_arm(axs[1], 0, arm_len, arm_radius, muscle_depth, muscle_radius, neg_lead_z, pos_lead_z, z_rings,
                 [q_out_rest] * len(z_rings), cmap, q_out_rest, q_out_ap)
        axs[0].set_xlabel('Time (s)')
        axs[0].set_ylabel('Voltage (V)')
        fig.tight_layout()
        frame_info = []
        # plt.show()

    t = t_start
    while t <= t_end:
        pos_lead_pot, neg_lead_pot = 0, 0
        # z_ap_max = t * v_ap
        # z_ap_min = z_ap_max - n_points_ap * arm_len / n_rings_z
        z_ap = t * v_ap
        for ring_z in z_rings:
            t_ap = t - ring_z / v_ap

            q_out = q_out_rest
            q_in = q_in_rest
            if ring_z < z_ap:
                q_out = ap_charge(t_ap, charge_time, discharge_time, q_out_rest, q_out_ap, ap_charge_max)
                q_in = ap_charge(t_ap, charge_time, discharge_time, q_in_rest, q_in_ap, ap_charge_max)

            out_point_q = q_out / n_points_ring
            in_point_q = q_in / n_points_ring

            out_point_pos = np.array([out_x, out_y, ring_z])
            in_point_pos = np.array([in_x, in_y, ring_z])

            # print(f'{ring_z}cm, q_out={q_out}, q_in={q_in}')

            pos_lead_pot += np.sum(calc_point_pot_cm(pos_lead_pos, out_point_pos, out_point_q))
            pos_lead_pot += np.sum(calc_point_pot_cm(pos_lead_pos, in_point_pos, in_point_q))

            neg_lead_pot += np.sum(calc_point_pot_cm(neg_lead_pos, out_point_pos, out_point_q))
            neg_lead_pot += np.sum(calc_point_pot_cm(neg_lead_pos, in_point_pos, in_point_q))

            # old_pos_pot, old_neg_pot = pos_lead_pot, neg_lead_pot
            # for angle in np.linspace(0, 2*np.pi, n_points_ring):
            #     out_x = out_radius * np.cos(angle)
            #     out_y = -muscle_depth + out_radius * np.sin(angle)
            #     out_point_pos = np.array([out_x, out_y, ring_z])
            #     # q_out = q_out_ap if z_ap_min < ring_z <= z_ap_max else q_out_rest
            #
            #     in_x = in_radius * np.cos(angle)
            #     in_y = -muscle_depth + in_radius * np.sin(angle)
            #     in_point_pos = np.array([in_x, in_y, ring_z])
            #     # q_in = q_in_ap if z_ap_min < ring_z <= z_ap_max else q_in_rest
            #
            #     pos_lead_pot += calc_point_pot_cm(pos_lead_pos, out_point_pos, out_point_q)
            #     pos_lead_pot += calc_point_pot_cm(pos_lead_pos, in_point_pos, in_point_q)
            #
            #     neg_lead_pot += calc_point_pot_cm(neg_lead_pos, out_point_pos, out_point_q)
            #     neg_lead_pot += calc_point_pot_cm(neg_lead_pos, in_point_pos, in_point_q)
        ts.append(t)
        pos_lead_pots.append(pos_lead_pot)
        neg_lead_pots.append(neg_lead_pot)
        print(f't={t:.6f}s')
        # print(f't={t:.6f}s  |  q_in={q_in}  |  q_out={q_out}  | q_out_pos={out_point_pos}  | q_in_pos={in_point_pos}')
        # print(f'pos_lead_pot diff={pos_lead_pot - old_pos_pot}  |  neg_lead_pot diff={neg_lead_pot - old_neg_pot}')
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

    ts = np.array(ts)
    f_pos = interp1d(ts, pos_lead_pots, bounds_error=False, fill_value=pos_lead_pots[0])
    f_neg = interp1d(ts, neg_lead_pots, bounds_error=False, fill_value=neg_lead_pots[0])
    # ap_times = np.arange([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) * 4 * dt
    # ap_times = np.linspace(0, 0.05, 30)
    ap_times = np.random.normal(0.003, 0.001, 100)
    pos_lead_pots_sum, neg_lead_pots_sum = np.zeros(len(pos_lead_pots)), np.zeros(len(neg_lead_pots))
    plt.figure()
    for ap_t in ap_times:
        pos_lead_pots_sum += f_pos(ts - ap_t)
        neg_lead_pots_sum += f_neg(ts - ap_t)
        plt.plot(ts, f_pos(ts - ap_t))
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')

    plt.figure()
    plt.plot(ts, pos_lead_pots_sum, label='Positive Lead Sum')
    plt.plot(ts, neg_lead_pots_sum, label='Negative Lead Sum')
    plt.legend()
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.tight_layout()

    plt.figure()
    plt.grid()
    plt.plot(ts, np.array(pos_lead_pots_sum) - np.array(neg_lead_pots_sum), label='Sum Difference')
    plt.legend()
    plt.xlabel('Time (s)')
    plt.ylabel('Voltage (V)')
    plt.tight_layout()

    plt.show()


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


def plot_arm(ax, arm_z0, arm_zf, arm_radius, muscle_depth, muscle_radius, neg_lead_z, pos_lead_z, z_charges,
             z_charge_seps, cmap, q_rest, q_ap):
    ax.plot([arm_z0, arm_zf], [0, 0], color='black')
    ax.plot([arm_z0, arm_zf], [-arm_radius * 2, -arm_radius * 2], color='black')
    ax.scatter([neg_lead_z], [muscle_depth * 0.02], marker='o', color='orange', label='Negative Lead')
    ax.scatter([pos_lead_z], [muscle_depth * 0.02], marker='+', color='red', label='Positive Lead')
    lines = {}
    for z, z_charge_sep in zip(z_charges, z_charge_seps):
        color_scale = (z_charge_sep - q_rest) / (q_ap - q_rest) * cmap.N
        color = cmap(color_scale)
        print(z, z_charge_sep, color, color_scale)
        line, = ax.plot([z, z], [-muscle_depth + muscle_radius, -muscle_depth - muscle_radius], color=color, lw=1)
        lines.update({z: line})
    ax.set_xlabel('Along Arm (cm)')
    ax.set_ylabel('Depth in Arm (cm)')
    ax.set_aspect('equal')

    return lines


def calc_point_pot_cm(obs_pos, point_pos, point_q):
    return k * point_q / (np.linalg.norm(obs_pos - point_pos) / 100)


def weibull_function(t, k_shape, lam):
    return (k_shape / lam) * (t / lam)**(k_shape - 1) * np.exp(-(t / lam)**k_shape)


def ap_function(x, b, c):
    return (1 - np.exp(-x / b)) * np.exp(-x / c)


def ap_charge(t, tau_charge, tau_discharge, q_rest, q_ap, ap_func_max):
    # return (q_ap - q_rest) / weibull_max * weibull_function(t, k_shape, lam) + q_rest
    if type(t) is np.ndarray:
        t[t < 0] = 0
    else:
        t = t if t >= 0 else 0
    return(q_ap - q_rest) / ap_func_max * ap_function(t, tau_charge, tau_discharge) + q_rest


def charged_cylinder_potential():
    arm_len = 30.  # cm
    lead_z = 15.  # cm
    muscle_depth = 1.  # cm
    muscle_radii = np.linspace(0.0e-6 * 100, 2e-6 * 100, 100)  # cm

    n_rings_z = 151
    n_points_ring = 50
    q_out = +1e-10  # C Total charge of rings

    lead_pos = np.array([0, 0, lead_z])
    z_rings = np.linspace(0, arm_len, n_rings_z)

    angles = np.linspace(0, 2 * np.pi, n_points_ring)

    potentials = []
    for muscle_radius in muscle_radii:
        out_x = muscle_radius * np.cos(angles)
        out_y = -muscle_depth + muscle_radius * np.sin(angles)

        lead_pot = 0
        for ring_z in z_rings:
            out_point_q = q_out / n_points_ring
            out_point_pos = np.array([out_x, out_y, ring_z])
            lead_pot += np.sum(calc_point_pot_cm(lead_pos, out_point_pos, out_point_q))
        potentials.append(lead_pot)

    plt.grid()
    plt.plot(muscle_radii * 1e4, potentials)
    plt.xlabel(r'Cylinder Radius ($\mu m$)')
    plt.ylabel(r'Electric Potential 1cm Above Center of Cylinder (V)')
    plt.show()


if __name__ == '__main__':
    main()
