import matplotlib.pyplot as plt
import random
import numpy as np
import sensors
import socket_connect

plt.ion()  # turning interactive mode on

# preparing the data
size = 1000
number_sensors = 1
i = 0
y = np.zeros((1, size))
x = np.linspace(0, 2, size)

sock = socket_connect.connect_to_s_test('192.168.1.77')
dummy = sensors.BMA280("SPI", 100, 3, 4, sock)

def shift(x_s, n, value):
    e = np.empty_like(x_s)
    if n >= 0:
        e[:, :n] = value
        e[:, n:] = x_s[:, :-n]
    else:
        e[: ,n:] = value
        e[:, :n] = x_s[:, -n:]
    return e

# plotting the first frame
for j in range(number_sensors):
    y_plot = y[j, :]
    graph = plt.plot(x,y_plot, color='C0')[0]
plt.ylim(-2,2)
plt.show(block=False)
plt.pause(1)

# the update loop
while(True):
    # updating the data
    sensor_data = dummy.get_dummy_sin(i)
    y = shift(y, -1, sensor_data)
    
    # removing the older graph
    graph.remove()
    
    # plotting newer graph
    for j in range(number_sensors):
        y_plot = y[j, :]
        graph = plt.plot(x,y_plot, color='C0')[0]
    plt.xlim(x[0], x[-1])
    
    # calling pause function for 0.25 seconds
    plt.pause(0.005)
    i += 1