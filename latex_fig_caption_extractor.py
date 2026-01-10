#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on January 10 2:44 PM 2026
Created in PyCharm
Created as Misc/latex_fig_caption_extractor.py

@author: Dylan Neff, Dylan
"""

import re


def main():
    tex_file_path = 'C:/Users/Dylan/Downloads/STAR_Proton_Azimuthal_Clustering_Analysis_Note/main.tex'
    out_file_path = 'C:/Users/Dylan/Downloads/STAR_Proton_Azimuthal_Clustering_Analysis_Note/fig_captions.txt'
    captions = extract_captions_from_figures(tex_file_path)
    for i, caption in enumerate(captions, 1):
        print(f"{i}: {caption}")

    # Save captions to output file with numbering
    with open(out_file_path, 'w', encoding='utf-8') as out_file:
        for i, caption in enumerate(captions, 1):
            out_file.write(f"{i}: {caption}\n")

    print('donzo')



def extract_captions_from_figures(tex_path):
    """
    Read a LaTeX .tex file, find all \\begin{figure} ... \\end{figure} blocks,
    and extract the text from each \\caption{...}.
    Returns a list of caption strings.
    """
    with open(tex_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Find all figure environments (multiline, non-greedy)
    figure_blocks = re.findall(
        r'\\begin\{figure\}.*?\\end\{figure\}',
        text,
        re.DOTALL
    )

    captions = []
    for block in figure_blocks:
        caption = extract_command_argument(block, "caption")
        if caption is not None:
            captions.append(caption.strip())

    return captions


def extract_command_argument(text, command):
    """
    Extract the argument of a LaTeX command like \\command{...}
    while correctly handling nested braces.
    Returns the inner string, or None if not found.
    """
    pattern = r'\\' + re.escape(command) + r'\s*\{'
    match = re.search(pattern, text)
    if not match:
        return None

    start = match.end()
    depth = 1
    i = start

    while i < len(text) and depth > 0:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1

    if depth != 0:
        # Unbalanced braces
        return None

    return text[start:i-1]



if __name__ == '__main__':
    main()
