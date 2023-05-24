#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 14 8:24 PM 2023
Created in PyCharm
Created as Misc/get_gradescope_distributions

@author: Dylan Neff, Dylan
"""
import os.path
import time
from time import sleep
import string
import random

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.gridspec as gridspec
import seaborn as sns
import pandas as pd

import selenium.common.exceptions
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from GradescopeNavigator import GradescopeDistributionGetter as GsDG


def main():
    csv_directory_path = 'N:/UCLA_Microsoft/OneDrive - personalmicrosoftsoftware.ucla.edu/' \
                         'Tablet_Store/UCLA/TA/Phys 5CL/Spring_2023/Grade_Distributions/'
    # get_grade_distributions(csv_directory_path)
    # lab_type = 'lab'
    # lab_num = 6
    # # selenium_test()
    # csv_path = gsn_get_distribution(lab_type, lab_num)
    # plot_lab(f'C:/Users/Dylan/Desktop/{lab_type}{lab_num}_dists.csv', prelab=True if lab_type == 'prelab' else False)
    # plot_lab('C:/Users/Dylan/Desktop/lab3_dists.csv', prelab=False)
    plot_total(csv_directory_path)
    print('donzo')


def get_grade_distributions(csv_directory_path='C:/Users/Dylan/Desktop/'):
    lab_types = ['prelab', 'lab']
    lab_nums = [1, 2, 3, 4, 5, 6]
    # selenium_test()
    for lab_type in lab_types:
        for lab_num in lab_nums:
            if lab_num == 1 and lab_type == 'prelab':
                continue
            csv_path = gsn_get_distribution(lab_type, lab_num, False, csv_directory_path)
    # plot_lab(f'C:/Users/Dylan/Desktop/{lab_type}{lab_num}_dists.csv', prelab=True if lab_type == 'prelab' else False)


def gsn_get_distribution(lab_type, lab_num, overwrite_csv=False, csv_dir='C:/Users/Dylan/Desktop/'):
    section_flags = ['5CL-G']
    # assignment_name = 'Week 1 Assignment & Lab Credit'
    assignment_name = f'5C {"Pre-Lab" if lab_type == "prelab" else "Lab"} {lab_num}'
    prelab = True if 'Pre-Lab' in assignment_name else False
    assignment_name_alt = 'lab 1'
    distribution_getter = GsDG()
    assignment_type_name = 'prelab' if prelab else 'lab'
    csv_path = f'{csv_dir}{assignment_type_name}{lab_num}_dists.csv'

    if lab_num == 1:
        assignment_name = '5CL Week 1 Assignment & Lab Credit'

    if os.path.exists(csv_path):
        if overwrite_csv:
            print(f'Path exists, will overwrite {csv_path}')
        print(f'{csv_path}')
        return csv_path
    # distribution_getter = GsDG('C:/Users/Dyn04/Desktop/Creds/gradescope_creds.txt')
    df = []
    for section in distribution_getter.get_sections():
        if any(flag in section for flag in section_flags):
            print(section)
            df_section = distribution_getter.get_distribution(section, assignment_name)
            if len(df_section) == 0 and lab_num == 1:
                df_section = distribution_getter.get_distribution(section, assignment_name_alt)
            df.extend(df_section)
    # distribution_getter.close()
    df = pd.DataFrame(df)
    # df.to_csv('C:/Users/Dylan/Desktop/prelab2_dists.csv', index=False)
    df.to_csv(csv_path, index=False, mode='w')
    print(f'Writing {assignment_name} to {csv_path}')
    # plot_lab(csv_path, prelab)


def combine_csvs(csv_dir):
    dfs = []
    for file_name in os.listdir(csv_dir):
        if '.csv' in file_name:
            df = pd.read_csv(f'{csv_dir}{file_name}')
            df['possible'] = df['assignment'].apply(lambda assign: 8. if 'Pre-Lab' in assign else 20.)
            dfs.append(df)

    return pd.concat(dfs)


def plot_lab(path=None, prelab=False):
    if path is None:
        path = 'C:/Users/Dylan/Desktop/lab1_dists.csv'
    df = pd.read_csv(path)

    min_grade = 0
    max_grade = 8 if prelab else 20

    fig_ungraded, ax_ungraded = plt.subplots(dpi=144)
    sns.countplot(x='ta', data=df[~df['graded']])
    ax_ungraded.set_title('Number Ungraded')
    df = df[df['graded']]

    # df = df[df['section'] != '5CL-G30']
    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='ta', multiple='stack')
    ax_tas.set_title('All Grades')
    df_scored = df[(df['score'] != min_grade) & (df['score'] != max_grade)]
    # df = df[(df['score'] != 0) & (df['score'] != 20)]
    # print(df[df['ta'] == 'Dylan'])
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.histplot(data=df_scored, x='score', hue='section')
    ax_courses.set_title('No Min/Max Grades')
    fig_coures, ax_courses = plt.subplots(dpi=144)
    # sns.kdeplot(data=df_scored, x='score', hue='section')
    sns.rugplot(data=df_scored, x='score', hue='section')
    # for section in pd.unique(df['section']):
    #     df_section = df[df['section'] == section]
    #     sns.histplot(df_section['score'], label=section)
    # plt.legend()

    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.histplot(data=df_scored, x='score', hue='ta', multiple='stack')
    ax_tas.set_title('No Min/Max Grades')
    fig_tas, ax_tas = plt.subplots(dpi=144)
    # sns.kdeplot(data=df_scored, x='score', hue='ta')
    sns.rugplot(data=df_scored, x='score', hue='ta')
    # for ta_name in pd.unique(df['ta']):
    #     df_ta = df[df['ta'] == ta_name]
    #     sns.histplot(df_ta['score'], label=ta_name)
    # plt.legend()

    fig_tas, ax_tas = plt.subplots(dpi=144)
    ta_mean_sd_df = df.groupby('ta')['score'].agg(['mean', 'std']).reset_index()
    # ta_grouped = df.groupby('ta')
    ax_tas.axhline(8 if prelab else 20, color='black')
    # quartile_errorbars = [ta_mean_sd_df['mean'] - ta_grouped['score'].quantile(0.25).values,
    #                       ta_grouped['score'].quantile(0.75).values - ta_mean_sd_df['mean']]
    # print(ta_mean_sd_df['mean'] - ta_grouped['score'].quantile(0.25).values)
    ax_tas.errorbar(ta_mean_sd_df['ta'], ta_mean_sd_df['mean'], yerr=ta_mean_sd_df['std'], marker='o', ls='none')
    # ax_tas.errorbar(ta_mean_sd_df['ta'], ta_mean_sd_df['mean'], yerr=quartile_errorbars, marker='o', ls='none')
    ax_tas.scatter(df['ta'], df['score'], marker='_', alpha=0.2)
    plt.xticks(rotation=45)
    ax_tas.set_ylabel('Average Score')
    plt.tight_layout()

    plt.show()


def plot_total(csv_dir='C:/Users/Dylan/Desktop/'):
    df = combine_csvs(csv_dir)

    alias = True
    ta_col = 'ta_alias' if alias else 'ta'
    ta_names = df['ta'].unique()
    random.shuffle(ta_names)
    ta_map = dict(zip(ta_names, [f'TA {x}' for x in list(string.ascii_uppercase)[:len(ta_names)]]))
    print(ta_map)
    df['ta_alias'] = df['ta'].map(ta_map)

    df['assign_count'] = 1

    df_graded = df.groupby(ta_col).sum()
    df_graded['frac_graded'] = df_graded['graded'] / df_graded['assign_count']
    df_graded = df_graded.reset_index()

    df = df[df['graded']]
    df_ta = df.groupby([ta_col, 'student_name']).sum()
    df_ta['percent'] = df_ta['score'] / df_ta['possible']
    df_ta_ungrouped = df_ta.reset_index()

    fig_tas = plt.figure(figsize=(8, 6), dpi=144)
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 2.5])
    ax_bar = plt.subplot(gs[0])
    ax_tas = plt.subplot(gs[1], sharex=ax_bar)

    ax_tas.grid()
    ta_mean_sd_df = df_ta.groupby(ta_col)['percent'].agg(['mean', 'std']).reset_index()
    ax_tas.axhline(1, color='black')
    ax_tas.errorbar(ta_mean_sd_df[ta_col], ta_mean_sd_df['mean'], yerr=ta_mean_sd_df['std'], marker='o', ls='none')
    ax_tas.scatter(df_ta_ungrouped[ta_col], df_ta_ungrouped['percent'], marker='_', alpha=0.2)
    plt.xticks(rotation=45)
    ax_tas.set_ylabel('Total Score')
    ax_tas.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=0))

    ax_bar.bar(df_graded[ta_col], df_graded['frac_graded'])
    ax_bar.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1, decimals=0))
    ax_bar.set_ylabel('Assignments Graded')
    ax_bar.set_ylim(top=1.0)

    fig_tas.subplots_adjust(hspace=0.0)
    fig_tas.tight_layout()
    fig_tas.subplots_adjust(hspace=0.0)

    plt.show()


if __name__ == '__main__':
    main()
