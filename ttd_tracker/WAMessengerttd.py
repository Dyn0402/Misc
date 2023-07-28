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


class WAMessengerttd:
    """
    Send WhatsApp messages using API with account information read in from self.data_path
    """
    def __init__(self):
        self.data_paths = [
            './wamessenger_data_ttd.txt',
            'C:/Users/Dylan/Desktop/wamessenger_data_ttd.txt',
        ]
        self.default_template_name = 'rcf_message'
        self.data_path = self.try_paths()
        self.key, self.phone_send, self.token = None, None, None
        self.phone_receive_dict = {}
        self.cipher_suite = None
        self.read_account_data()
        self.url, self.headers, self.req_data = self.set_request_fields()

    def set_request_fields(self):
        url = f'https://graph.facebook.com/v16.0/{self.phone_send}/messages'
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

        phone = self.phone_receive_dict['dylan'] if 'dylan' in self.phone_receive_dict \
            else list(self.phone_receive_dict.values())[0]
        data = {
            'messaging_product': 'whatsapp',
            'to': phone,
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
            lines = file.readlines()
        self.key = lines.pop(0)
        self.cipher_suite = Fernet(bytes(self.key, 'utf-8'))
        self.phone_send = self.cipher_suite.decrypt(bytes(lines.pop(0), 'utf-8')).decode('utf-8')
        self.token = self.cipher_suite.decrypt(bytes(lines.pop(0), 'utf-8')).decode('utf-8')
        for line in lines:
            line = line.split(' ')
            name = self.cipher_suite.decrypt(bytes(line[0], 'utf-8')).decode('utf-8')
            number = self.cipher_suite.decrypt(bytes(line[1], 'utf-8')).decode('utf-8')
            self.phone_receive_dict.update({name: number})

    def send_message(self, message=None, template_name=None, receive_name=None):
        """
        Send message to whatsapp number
        :param message: Message to send
        :param template_name: Name of template,
        :param receive_name: Name of person to send message to
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
        if receive_name is not None and receive_name in self.phone_receive_dict:
            data['to'] = self.phone_receive_dict[receive_name]

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


def write_encrypt_file():
    pass


def read_encrypt_file():
    path = 'C:/Users/Dylan/Desktop/wamessenger_data_ttd.txt'
    with open(path, 'r') as file:
        lines = file.readlines()
    key = lines.pop(0)
    cipher_suite = Fernet(bytes(key, 'utf-8'))
    phone_send = cipher_suite.decrypt(bytes(lines.pop(0), 'utf-8')).decode('utf-8')
    token = cipher_suite.decrypt(bytes(lines.pop(0), 'utf-8')).decode('utf-8')
    print(phone_send, token)
    for line in lines:
        line = line.split(' ')
        name = cipher_suite.decrypt(bytes(line[0], 'utf-8')).decode('utf-8')
        number = cipher_suite.decrypt(bytes(line[1], 'utf-8')).decode('utf-8')
        print(name, number)


if __name__ == '__main__':
    read_encrypt_file()
