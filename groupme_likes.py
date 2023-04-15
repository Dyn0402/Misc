#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on April 14 10:25 PM 2023
Created in PyCharm
Created as Misc/groupme_likes.py

@author: Dylan Neff, Dylan
"""

import requests
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from groupy.client import Client


def main():
    # write_messages_to_csv()
    plot_messages()
    print('donzo')


def plot_messages():
    df = pd.read_csv('C:/Users/Dylan/Desktop/harambe_groupme.csv')
    df = df.drop('Unnamed: 0', axis=1)
    df['date'] = pd.to_datetime(df['created_at'], unit='s')
    uid_name_map = get_uid_name_map(df)
    df['real_name'] = df['user_id'].map(uid_name_map)

    num_printed = 0
    for index, row in df.sort_values(by='likes', ascending=False).iterrows():
        print(f'{row.date} {row.real_name} - {row.likes} likes: {row["text"]}')
        num_printed += 1
        if num_printed > 10:
            break

    print()

    num_printed = 0
    for index, row in df.sort_values(by='date').iterrows():
        print(f'{row.date} {row.real_name} - {row.likes} likes: {row["text"]}')
        num_printed += 1
        if num_printed > 10:
            break

    cmap = plt.cm.get_cmap("winter")

    fig, ax = plt.subplots(dpi=144)
    like_totals = df.groupby('real_name').sum().sort_values(by='likes', ascending=False)
    sns.barplot(x=like_totals.index, y='likes', data=like_totals)
    for i, likes in enumerate(like_totals['likes']):
        plt.gca().get_children()[i].set_facecolor(cmap(likes / like_totals['likes'].max()))
    ax.set_ylabel('Total Likes')
    ax.set_xlabel(None)
    fig.tight_layout()

    fig, ax = plt.subplots(dpi=144)
    like_averages = df.groupby('real_name').mean().sort_values(by='likes', ascending=False)
    sns.barplot(x=like_averages.index, y='likes', data=like_averages)
    for i, likes in enumerate(like_averages['likes']):
        plt.gca().get_children()[i].set_facecolor(cmap(likes / like_averages['likes'].max()))
    ax.set_ylabel('Average Likes per Message')
    ax.set_xlabel(None)
    fig.tight_layout()

    fig, ax = plt.subplots(dpi=144)
    message_totals = df['real_name'].value_counts()
    print(message_totals)
    sns.barplot(x=message_totals.index, y=message_totals.values)
    for i, messages in enumerate(message_totals.values):
        plt.gca().get_children()[i].set_facecolor(cmap(messages / message_totals.values.max()))
    ax.set_ylabel('Total Messages')
    ax.set_xlabel(None)
    fig.tight_layout()

    date_messages = df.groupby(pd.Grouper(key='date', freq='M')).size()
    date_messages = date_messages.reset_index(name='counts')
    sns.set_style('darkgrid')
    fig, ax = plt.subplots(dpi=144)
    sns.lineplot(x='date', y='counts', data=date_messages.iloc[:-1])
    date_messages = df.groupby(pd.Grouper(key='date', freq='Y')).size() / 12
    date_messages = date_messages.reset_index(name='counts')
    sns.lineplot(x='date', y='counts', data=date_messages.iloc[:-1])
    ax.set_ylabel('Group Messages per Month')
    ax.set_xlabel(None)
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    date_likes = df.groupby(pd.Grouper(key='date', freq='M'))['likes'].sum().reset_index(name='likes')
    sns.set_style('darkgrid')
    fig, ax = plt.subplots(dpi=144)
    sns.lineplot(x='date', y='likes', data=date_likes.iloc[:-1])
    date_messages = df.groupby(pd.Grouper(key='date', freq='Y')).size() / 12
    date_messages = date_messages.reset_index(name='counts')
    sns.lineplot(x='date', y='counts', data=date_messages.iloc[:-1])
    ax.set_ylabel('Group Likes per Month')
    ax.set_xlabel(None)
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    date_likes = df.groupby(pd.Grouper(key='date', freq='M'))['likes'].mean().reset_index(name='likes')
    sns.set_style('darkgrid')
    fig, ax = plt.subplots(dpi=144)
    sns.lineplot(x='date', y='likes', data=date_likes)
    # date_messages = df.groupby(pd.Grouper(key='date', freq='Y')).mean() / 12
    # date_messages = date_messages.reset_index(name='counts')
    # sns.lineplot(x='date', y='counts', data=date_messages.iloc[:-1])
    ax.set_ylabel('Average Likes Per Message')
    ax.set_xlabel(None)
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    df_nick = df[df['real_name'] == 'Nick']
    date_messages = df_nick.groupby(pd.Grouper(key='date', freq='M')).size().reset_index(name='counts')
    sns.set_style('darkgrid')
    fig, ax = plt.subplots(dpi=144)
    sns.lineplot(x='date', y='counts', data=date_messages.iloc[:-1])
    date_messages = df_nick.groupby(pd.Grouper(key='date', freq='Y')).size() / 12
    date_messages = date_messages.reset_index(name='counts')
    sns.lineplot(x='date', y='counts', data=date_messages.iloc[:-1])
    ax.set_ylabel('Nick Messages per Month')
    ax.set_xlabel(None)
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    date_messages = df.groupby(['real_name', pd.Grouper(key='date', freq='Y')]).size().reset_index(name='counts')
    # date_messages = date_messages.reset_index(name='counts')
    date_messages = date_messages[date_messages['date'].dt.year != 2023]
    sns.set_style('darkgrid')
    fig, ax = plt.subplots(dpi=144)
    sns.lineplot(x='date', y='counts', hue='real_name', data=date_messages.iloc[:-1])
    ax.set_ylabel('Group Messages per Year')
    ax.set_xlabel(None)
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    plt.show()


def get_uid_name_map(df, print_uid_alias=False):
    if print_uid_alias:
        for uid in pd.unique(df['user_id']):
            print(uid, [alias for alias in pd.unique(df[df['user_id'] == uid]['name'])])

    uid_name_map = {
        '8677786': 'Bryan',
        '9078837': 'Alex',
        '11591273': 'Matt',
        '11333879': 'Austin',
        '11333878': 'Sam',
        '7046969': 'Clay',
        '24467902': 'Charlie',
        '7183540': 'Noah',
        '11334321': 'Jacob',
        '15806146': 'Blake',
        '11743921': 'Nick',
        '6463933': 'Dylan'
    }

    return uid_name_map


def write_messages_to_csv():
    token = '***REMOVED***'
    group_name = 'Take A Shot For Harambe, He Took One For You'
    df = get_group_messages(group_name, token)
    df.to_csv('C:/Users/Dylan/Desktop/harambe_groupme.csv')


def get_group_id(group_name, token):
    url = 'https://api.groupme.com/v3/groups'

    headers = {
        'Content-Type': 'application/json',
        'X-Access-Token': token
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        groups = response.json()['response']
        for group in groups:
            if group['name'] == group_name:
                return group['id']

    return None


def get_group_messages(group_name, token):
    group_id = get_group_id(group_name, token)

    df = []
    last_message_id = None

    headers = {
        'Content-Type': 'application/json',
        'X-Access-Token': token
    }

    params = {
        'limit': 100
    }

    # num_messages = 0
    while True:
        url = f'https://api.groupme.com/v3/groups/{group_id}/messages'
        if last_message_id is not None:
            url += f'?before_id={last_message_id}'
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            messages = response.json()['response']['messages']
            last_id = messages[-1]['id']
            if last_message_id == last_id:
                break
            for message in messages:
                df.append({
                    'name': message['name'],
                    'user_id': message['user_id'],
                    'created_at': message['created_at'],
                    'likes': len(message['favorited_by']),
                    'liked_by': message['favorited_by'],
                    'text': message['text']
                })
            last_message_id = last_id
            print(datetime.fromtimestamp(messages[-1]['created_at']).strftime('%B %d, %Y'))
            # num_messages += 100
            # if num_messages > 2000:
            #     break
        else:
            print('Bad response ', response.status_code)
            break

    return pd.DataFrame(df)


def groupy():
    # No likes functionality
    token = '***REMOVED***'
    client = Client.from_token(token)

    for group in client.groups.list():
        if 'Harambe' in group.name:
            print(group.id)
            # print(list(group.messages.list().autopage())[-1])
            print(list(group.messages.list())[-1])

    # group = client.groups.get(4575471)
    # message = group.messages.get(168141414059076448)
    # print(message)

    # print([l for l in client.groups.list()])


if __name__ == '__main__':
    main()
