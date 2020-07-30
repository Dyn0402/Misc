#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on November 23 12:35 PM 2019
Created in PyCharm
Created as Misc/plex_renamer.py

@author: Dylan Neff, dylan
"""

import os
import shutil
import re
import tvdbsimple as tvdb

tvdb.KEYS.API_KEY = '20503FE8-5959-4849-88CC-2A0B8E9E8B2A'


def main():
    hunterx()


def naruto_box_to_season():
    # path = '/home/dylan/local_server/dyn0402/Torrents/TV Shows/Naruto Shippuden/'
    path = 'C:/Users/Dylan/Torrents/TV Shows/Naruto Shippuden/'
    search = tvdb.Search()
    response = search.series('Naruto Shippuden')
    show = tvdb.Series(search.series[0]['id'])
    response = show.info()
    print(show.seriesName)
    episodes = show.Episodes.all()
    print(episodes[300])

    for box in range(32, 34):
        box_path = path + f'Box Set {box}' + '/'
        # box_path = [x[0] for x in os.walk(box_path)][1]+'/'
        # print(box_path)
        original_files = os.listdir(box_path)
        # print(original_files)
        for file in original_files:
            extension = get_extension(file)
            if extension == 'txt':
                continue
            abs_episode = get_ndig_ep(file, n=3)
            if abs_episode in range(413, 417):
                episode = next(ep for ep in episodes if ep['absoluteNumber'] == abs_episode)
                season = episode['airedSeason']
                episode_name = str(episode['absoluteNumber']) + ' ' + episode['episodeName']
                episode_name = episode_name.replace('/', 'and')
                name = file_name_format(show.seriesName, season, episode['airedEpisodeNumber'], episode_name, extension)
                source = box_path + file
                dest = path + folder_name_format(season) + '/' + name
                print(source)
                print(dest)
                print()
                shutil.move(source, dest)


def make_season_dirs(path, start, end):
    for season in range(start, end+1):
        os.mkdir(path+folder_name_format(season))


def naruto_add_ep_names():
    path = 'C:/Users/Dylan/Torrents/TV Shows/Naruto Shippuden/'
    search = tvdb.Search()
    response = search.series('Naruto Shippuden')
    show = tvdb.Series(search.series[0]['id'])
    response = show.info()
    print(show.seriesName)
    episodes = show.Episodes.all()

    for season_num in range(17, 19):
        season_path = path + folder_name_format(season_num) + '/'
        original_files = os.listdir(season_path)
        for file in original_files:
            extension = get_extension(file)
            # abs_episode = get_ndig_ep(file, n=3)
            # episode = next(ep for ep in episodes if ep['absoluteNumber'] == abs_episode)
            # season = episode['airedSeason']
            # episode_name = str(episode['absoluteNumber']) + ' ' + episode['episodeName']
            # episode_name = episode_name.replace('/', 'and')
            # episode_name = episode_name.replace(':', '-')
            # name = file_name_format(show.seriesName, season, episode['airedEpisodeNumber'], episode_name, extension)
            season, episode = get_sxxexx(file)
            episode_name = next(str(ep['absoluteNumber']) + ' ' + ep['episodeName'] for ep in episodes
                                if ep['airedEpisodeNumber'] == episode and ep['airedSeason'] == season)
            name = file_name_format(show.seriesName, season, episode, episode_name, extension)
            source = season_path + file
            dest = season_path + name
            print(source)
            print(dest)
            print()
            os.rename(source, dest)
            # shutil.move(source, dest)


def naruto_18():
    path = '/home/dylan/local_server/dyn0402/Torrents/TV Shows/Naruto Shippuden/'
    search = tvdb.Search()
    response = search.series('Naruto Shippuden')
    show = tvdb.Series(search.series[0]['id'])
    response = show.info()
    print(show.seriesName)
    episodes = show.Episodes.all()
    # print(episodes[300])
    # print([episode['episodeName'] for episode in episodes if episode['airedSeason'] == 17])

    original_files = os.listdir(path+'Season 18')
    for file in original_files:
        extension = get_extension(file)
        season, episode = get_sxxexx(file)
        season -= 1
        episode += 11
        episode_name = next(ep['episodeName'] for ep in episodes
                            if ep['airedEpisodeNumber'] == episode and ep['airedSeason'] == season)
        name = file_name_format(show.seriesName, season, episode, episode_name, extension)
        source = path + 'Season 18/' + file
        dest = path + 'Season 17/' + name
        print(source)
        print(dest)
        print()
        # shutil.move(source, dest)


def mandalorian():
    path = '/home/dylan/local_server/dyn0402/Torrents/TV Shows/The Mandalorian/Season 1/'
    search = tvdb.Search()
    response = search.series('The Mandalorian')
    show = tvdb.Series(search.series[0]['id'])
    response = show.info()
    episodes = show.Episodes.all()

    original_files = os.listdir(path)
    for file in original_files:
        extension = get_extension(file)
        season, episode = get_sxxexx(file)
        episode_name = next(ep['episodeName'] for ep in episodes if ep['airedEpisodeNumber'] == episode)
        print(episode_name)
        name = file_name_format(show.seriesName, season, episode, episode_name, extension)
        source = path + file
        dest = path + name
        print()
        print(source)
        print(dest)
        shutil.move(source, dest)


def hunterx():
    path = 'C:/Users/Dylan/Torrents/TV Shows/Hunter x Hunter/Series/'
    search = tvdb.Search()
    response = search.series('Hunter x Hunter (2011)')
    show = tvdb.Series(search.series[0]['id'])
    response = show.info()
    episodes = show.Episodes.all()
    print(episodes[0])
    for ep in episodes:
        print(f"{ep['airedEpisodeNumber']}  |  {ep['absoluteNumber']}")

    original_files = os.listdir(path)
    for file in original_files:
        extension = get_extension(file)
        season, episode_num = get_sxxexxx(file)
        ep = next(ep for ep in episodes if ep['absoluteNumber'] == episode_num)
        episode = ep['airedEpisodeNumber']
        season = ep['airedSeason']
        episode_name = check_file_name(ep['episodeName'])
        print()
        print(episode_name)
        name = file_name_format(show.seriesName, season, episode, episode_name, extension)
        source = path + file
        dest = path + name
        print(source)
        print(dest)
        shutil.move(source, dest)


def folder_name_format(season):
    name = 'Season ' + f'{season:02d}'
    return name


# Naruto Shippuden
def file_name_format(show_name, season_num, episode_num, episode_name, extension):
    name = f'{show_name} - s{season_num:02d}e{episode_num:02d} - {episode_name}.{extension}'
    return name


def get_extension(file):
    return file.split('.')[-1]


def get_sxxexx(file):
    name = file.split('/')[-1].lower()
    se = re.search('s..e..', name).group(0)
    season = int(se[1:3])
    episode = int(se[4:6])

    return season, episode


def get_sxxexxx(file):
    name = file.split('/')[-1].lower()
    se = re.search('s..e...', name).group(0)
    season = int(se[1:3])
    episode = int(se[4:7])

    return season, episode


def get_ndig_ep(file, n=3):
    name = file.split('/')[-1].lower()
    episode = int(re.search(r'(\d{%d})' % n, name).group(0))

    return episode


def check_file_name(name):
    bad_chars = ['*', '.', '"', '/', '\\', '[', ']', ':', ';', '|', ',', '?']
    replace_char = '_'
    for bad_char in bad_chars:
        name = name.replace(bad_char, replace_char)

    return name


if __name__ == '__main__':
    main()
