#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 14 8:24 PM 2023
Created in PyCharm
Created as Misc/get_gradescope_distributions

@author: Dylan Neff, Dylan
"""

import time
from time import sleep

import numpy as np
import matplotlib.pyplot as plt
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
    lab_type = 'prelab'
    lab_num = 5
    # selenium_test()
    # gsn_get_distribution(lab_type, lab_num)
    plot_lab(f'C:/Users/Dylan/Desktop/{lab_type}{lab_num}_dists.csv', prelab=True if lab_type == 'prelab' else False)
    # plot_lab('C:/Users/Dylan/Desktop/lab3_dists.csv', prelab=False)
    print('donzo')


def gsn_get_distribution(lab_type, lab_num):
    section_flags = ['5CL-G']
    # assignment_name = 'Week 1 Assignment & Lab Credit'
    assignment_name = f'5C {"Pre-Lab" if lab_type == "prelab" else "Lab"} {lab_num}'
    prelab = True if 'Pre-Lab' in assignment_name else False
    assignment_name_alt = 'lab 1'
    distribution_getter = GsDG()
    assignment_type_name = 'prelab' if prelab else 'lab'
    assignment_num = int(assignment_name[-1])
    csv_path = f'C:/Users/Dylan/Desktop/{assignment_type_name}{assignment_num}_dists.csv'
    # distribution_getter = GsDG('C:/Users/Dyn04/Desktop/Creds/gradescope_creds.txt')
    df = []
    for section in distribution_getter.get_sections():
        if any(flag in section for flag in section_flags):
            print(section)
            df_section = distribution_getter.get_distribution(section, assignment_name)
            if len(df_section) == 0:
                df_section = distribution_getter.get_distribution(section, assignment_name_alt)
            df.extend(df_section)
    # distribution_getter.close()
    df = pd.DataFrame(df)
    # df.to_csv('C:/Users/Dylan/Desktop/prelab2_dists.csv', index=False)
    df.to_csv(csv_path, index=False, mode='w')
    print(csv_path)
    # plot_lab(csv_path, prelab)


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


if __name__ == '__main__':
    main()
