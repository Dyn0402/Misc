#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 14 12:48 AM 2025
Created in PyCharm
Created as Misc/adm_stats.py

@author: Dylan Neff, Dylan
"""

import os
import re

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


def main():
    # Define the file path
    base_path = "C:/Users/Dylan/Desktop/test/"  # Change this to the actual base path
    file_name = "adm_stats.txt"  # Change this to the actual file path
    file_path = os.path.join(base_path, file_name)

    # Read the file and extract valid rows
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # Define a regex pattern to match valid rows
    pattern = re.compile(r"^([A-Za-z0-9 .&-]+)\s+(\d+)\s+(\d+)\s+(\d+)$")

    # Extract valid rows
    filtered_data = []
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            filtered_data.append(match.groups())

    # Create a DataFrame
    df = pd.DataFrame(filtered_data, columns=["Job Title", "Age", "Not Selected", "Selected*"])

    # Convert numeric columns to integers
    df[["Age", "Not Selected", "Selected*"]] = df[["Age", "Not Selected", "Selected*"]].astype(int)

    # Display the DataFrame
    print(df)

    # Optionally, save to CSV
    df.to_csv(f"{base_path}adm_jobs.csv", index=False)
    print('donzo')


if __name__ == '__main__':
    main()
