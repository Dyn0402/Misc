#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on November 12 5:16 PM 2024
Created in PyCharm
Created as Misc/colorado_dmv_appts.py

@author: Dylan Neff, Dylan
"""

import numpy as np
import matplotlib.pyplot as plt

import googlemaps
import folium
from geopy.geocoders import Nominatim

import json
import requests
from bs4 import BeautifulSoup


def main():
    # addresses = get_addresses()
    # map_test(addresses)
    # map_test_google(addresses)
    # location_data = get_location_data(addresses)
    # save_to_file(location_data)
    location_data = read_location_data('locations.txt')
    print(location_data)
    plot_locations(location_data)
    print('donzo')


def get_addresses():
    # URL of the website to fetch
    url = 'https://coloradoappt.cxmflow.com/Appointment/Index/d74f48b1-33a9-428c-acd1-d7d1bfc9555c'

    # Fetch the HTML content from the URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        html_content = response.text
        print("HTML content fetched successfully.")

        # Parse the HTML content using BeautifulSoup
        # soup = BeautifulSoup(html_content, 'html.parser')

        # Print out the prettified HTML
        # print(soup.prettify())
        addresses = extract_names_and_addresses(html_content)
        return addresses
    else:
        print(f"Failed to retrieve HTML. Status code: {response.status_code}")


def extract_names_and_addresses(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find all divs with the class 'QflowObjectItem DataControlBtn'
    locations = soup.find_all('div', class_='QflowObjectItem DataControlBtn')

    # List to store extracted name and address pairs
    name_address_list = []

    for location in locations:
        # Extract name from the first <p> tag
        name = location.find('p').get_text(strip=True)

        # Extract address from the second <p> tag with class 'subtitle'
        address = location.find('p', class_='subtitle').get_text(strip=True)
        address = address.replace('\n', ' ').replace('\r', '')

        # Append the name and address as a tuple to the list
        name_address_list.append((name, address))

    return name_address_list


def map_test(names_addresses):
    # List of addresses to plot

    addresses = [address for name, address in names_addresses]
    names = [name for name, address in names_addresses]

    # Initialize Nominatim geocoder
    geolocator = Nominatim(user_agent="geo_plotter")

    # Initialize list to store geocoded coordinates
    coordinates = []

    # Geocode each address and store coordinates
    for i, address in enumerate(addresses, start=1):
        location = geolocator.geocode(address)
        if location:
            coordinates.append((i, address, location.latitude, location.longitude))
            print(f"{i}. {address}")
        else:
            print(f"Could not geocode address: {address}")

    # Initialize a Colorado-centered map
    map_center = [39.5501, -105.7821]  # Rough center of Colorado
    map = folium.Map(location=map_center, zoom_start=7)

    # Add markers for each address
    for i, address, lat, lng in coordinates:
        folium.Marker(
            location=[lat, lng],
            popup=f"{i}. {address}",
            tooltip=f"{i}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(map)
        # Add a number marker on the map
        folium.Marker(
            [lat, lng],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 12pt; color : black">{i}</div>'
            )
        ).add_to(map)

    # Save the map to an HTML file
    map.save("colorado_addresses_map.html")
    print("Map saved as 'colorado_addresses_map.html'")


def map_test_google(names_addresses):
    # Replace with your Google Maps API key
    gmaps_api_key = 'AIzaSyDeqTM9njCPla8EFisNpAADriSCbwwdiv8'

    addresses = [address for name, address in names_addresses]
    names = [name for name, address in names_addresses]

    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=gmaps_api_key)

    # Initialize list to store geocoded coordinates
    coordinates = []

    # Geocode each address and store coordinates
    for i, address in enumerate(addresses, start=1):
        geocode_result = gmaps.geocode(address)

        if geocode_result:
            lat = geocode_result[0]['geometry']['location']['lat']
            lng = geocode_result[0]['geometry']['location']['lng']
            coordinates.append((i, address, lat, lng))
            print(f"{i}. {address}")
        else:
            print(f"Could not geocode address: {address}")

    # Initialize a Colorado-centered map
    map_center = [39.5501, -105.7821]  # Rough center of Colorado
    map = folium.Map(location=map_center, zoom_start=7)

    # Add markers for each address
    for i, address, lat, lng in coordinates:
        folium.Marker(
            location=[lat, lng],
            popup=f"{i}. {address}",
            tooltip=f"{i}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(map)
        # Add a number marker on the map
        folium.Marker(
            [lat, lng],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 12pt; color : black">{i}</div>'
            )
        ).add_to(map)

    # Save the map to an HTML file
    map.save("colorado_addresses_map.html")
    print("Map saved as 'colorado_addresses_map.html'")


def get_location_data(name_address_list):
    """
    Takes a list of (name, address) tuples, geocodes each address using Google Maps API,
    and returns a list of dictionaries with name, address, latitude, and longitude.
    """
    # Replace with your Google Maps API key
    gmaps_api_key = 'AIzaSyDeqTM9njCPla8EFisNpAADriSCbwwdiv8'

    # Initialize Google Maps client
    gmaps = googlemaps.Client(key=gmaps_api_key)

    location_data = []
    for name, address in name_address_list:
        try:
            geocode_result = gmaps.geocode(address)
            if geocode_result:
                lat = geocode_result[0]['geometry']['location']['lat']
                lng = geocode_result[0]['geometry']['location']['lng']
                location_data.append({
                    "name": name,
                    "address": address,
                    "latitude": lat,
                    "longitude": lng
                })
                print(f"Geocoded: {name}, {address}")
            else:
                print(f"Failed to geocode: {name}, {address}")
        except Exception as e:
            print(f"Error geocoding {name}, {address}: {e}")

    return location_data


def save_to_file(location_data, filename='locations.txt'):
    """
    Saves the location data to a text file in JSON format for easy reading and retrieval.
    """
    with open(filename, 'w') as file:
        json.dump(location_data, file, indent=4)
    print(f"Location data saved to {filename}")


def read_location_data(filename='locations.txt'):
    """
    Reads location data from a file and returns a list of dictionaries.
    """
    with open(filename, 'r') as file:
        location_data = json.load(file)
    return location_data


def plot_locations(location_data, map_center=[39.5501, -105.7821], zoom_start=7,
                   map_filename="colorado_addresses_map.html"):
    """
    Plots each location on a Colorado-centered map with the name as a marker label.
    """
    # Initialize the map centered on Colorado
    map_obj = folium.Map(location=map_center, zoom_start=zoom_start)

    # Add markers for each location
    for location in location_data:
        name = location['name']
        address = location['address']
        lat = location['latitude']
        lng = location['longitude']

        # Add a marker with the name as the tooltip
        folium.Marker(
            location=[lat, lng],
            popup=f"{name}<br>{address}",
            tooltip=name,
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(map_obj)

        # Optionally add a label with the name
        folium.Marker(
            location=[lat, lng],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 10pt; color : black">{name}</div>'
            )
        ).add_to(map_obj)

    # Save the map to an HTML file
    map_obj.save(map_filename)
    print(f"Map saved as '{map_filename}'")


if __name__ == '__main__':
    main()
