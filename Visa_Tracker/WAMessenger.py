#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on March 25 4:35 PM 2023
Created in PyCharm
Created as QGP_Scripts/WAMessenger

@author: Dylan Neff, Dylan
"""

from cryptography.fernet import Fernet
import json
import requests


class WAMessenger:
    """
    Send WhatsApp messages using API with account information read in from self.data_path
    """
    def __init__(self):
        self.data_paths = [
            './wamessenger_data.txt',
            'C:/Users/Dylan/Desktop/wamessenger_data.txt',
            '/star/u/dneff/wamessenger_data.txt'
        ]
        self.default_template_name = 'rcf_message'
        self.data_path = self.try_paths()
        self.key, self.phone_receive, self.phone_send, self.token = None, None, None, None
        self.cipher_suite = None
        self.read_account_data()
        self.url, self.headers, self.req_data = self.set_request_fields()

    def set_request_fields(self):
        url = f'https://graph.facebook.com/v16.0/{self.phone_send}/messages'
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        data = {
            'messaging_product': 'whatsapp',
            'to': self.phone_receive,
            'type': 'template',
            'template': {
                'name': self.default_template_name,
                'language': {
                    'code': 'en_US'
                }
            }
        }

        return url, headers, data

    def read_account_data(self):
        with open(self.data_path, 'r') as file:
            lines = [bytes(x, 'utf-8') for x in file.readlines()]
        self.key = lines.pop(0)
        self.cipher_suite = Fernet(self.key)
        self.phone_receive, self.phone_send, self.token = \
            [self.cipher_suite.decrypt(x).decode('utf-8') for x in lines[:3]]

    def send_message(self, message=None, template_name=None):
        """
        Send message to whatsapp number
        :param message: Message to send
        :param template_name: Name of template,
        :return:
        """
        data = self.req_data
        if message is not None:
            msg_body_params = [
                {
                    "type": "text",
                    "text": message
                }
            ]
            data['template'].update({'components': [{'type': 'body', 'parameters': msg_body_params}]})

        if template_name is not None:
            data['template']['name'] = template_name

        return requests.post(self.url, headers=self.headers, data=json.dumps(data))

    def try_paths(self):
        """
        Try all data file paths until one is successfully opened
        :return:
        """
        good_path = None
        for path in self.data_paths:
            try:
                open(path, 'r')
            except FileNotFoundError:
                continue
            good_path = path
            break
        assert good_path is not None
        return good_path
