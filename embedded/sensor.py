#!/usr/bin/env python3
from gpiozero import DistanceSensor
from time import sleep

# Initialize the DistanceSensor using GPIO Zero library
# Trigger pin is connected to GPIO 27, Echo pin to GPIO 17
#sensor = DistanceSensor(echo=17, trigger=27)
sensor = DistanceSensor(echo=23, trigger=6)
try:
    # Main loop to continuously measure and report distance
    while True:
        dis = sensor.distance * 100  # Measure distance and convert from meters to centimeters
        print('Distance: {:.2f} cm'.format(dis))  # Print the distance with two decimal precision
        sleep(0.5)  # Wait for 0.3 seconds before the next measurement

except KeyboardInterrupt:
    # Handle KeyboardInterrupt (Ctrl+C) to gracefully exit the loop
    pass
