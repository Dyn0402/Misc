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
    # selenium_test()
    gsn_get_distribution()
    # plot_lab1()
    print('donzo')


def gsn_get_distribution():
    section_flags = ['5CL-G4']
    # assignment_name = 'Week 1 Assignment & Lab Credit'
    assignment_name = '5C Pre-Lab 2'
    assignment_name_alt = 'lab 1'
    distribution_getter = GsDG()
    df = []
    for section in distribution_getter.get_sections():
        if any(flag in section for flag in section_flags):
            print(section)
            df_section = distribution_getter.get_distribution(section, assignment_name)
            if len(df_section) == 0:
                df_section = distribution_getter.get_distribution(section, assignment_name_alt)
            df.extend(df_section)
    distribution_getter.close()
    df = pd.DataFrame(df)
    df.to_csv('C:/Users/Dylan/Desktop/prelab2_dists.csv', index=False)
    plot_prelab2()


def plot_lab1():
    df = pd.read_csv('C:/Users/Dylan/Desktop/lab1_dists.csv')
    # df = df[df['section'] != '5CL-G30']
    df = df[(df['score'] != 0) & (df['score'] != 20)]
    print(df)
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='section')
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.kdeplot(data=df, x='score', hue='section')
    sns.rugplot(data=df, x='score', hue='section')
    # for section in pd.unique(df['section']):
    #     df_section = df[df['section'] == section]
    #     sns.histplot(df_section['score'], label=section)
    # plt.legend()

    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='ta', multiple='stack')
    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.kdeplot(data=df, x='score', hue='ta')
    sns.rugplot(data=df, x='score', hue='ta')
    # for ta_name in pd.unique(df['ta']):
    #     df_ta = df[df['ta'] == ta_name]
    #     sns.histplot(df_ta['score'], label=ta_name)
    # plt.legend()

    plt.show()


def plot_prelab2():
    df = pd.read_csv('C:/Users/Dylan/Desktop/prelab2_dists.csv')
    # df = df[df['section'] != '5CL-G30']
    df = df[(df['score'] != 0) & (df['score'] != 8)]
    print(df)
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='section')
    fig_coures, ax_courses = plt.subplots(dpi=144)
    sns.kdeplot(data=df, x='score', hue='section')
    sns.rugplot(data=df, x='score', hue='section')
    # for section in pd.unique(df['section']):
    #     df_section = df[df['section'] == section]
    #     sns.histplot(df_section['score'], label=section)
    # plt.legend()

    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.histplot(data=df, x='score', hue='ta', multiple='stack')
    fig_tas, ax_tas = plt.subplots(dpi=144)
    sns.kdeplot(data=df, x='score', hue='ta')
    sns.rugplot(data=df, x='score', hue='ta')
    # for ta_name in pd.unique(df['ta']):
    #     df_ta = df[df['ta'] == ta_name]
    #     sns.histplot(df_ta['score'], label=ta_name)
    # plt.legend()

    plt.show()


if __name__ == '__main__':
    main()
