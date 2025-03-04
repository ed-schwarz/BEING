import numpy as np
from matplotlib import pyplot as plt
from matplotlib import animation

i = 0
size = 10
sensor_data_array = np.zeros(size)
x = np.linspace(0, 2, size)
fig = plt.figure()

def shift(x_s, n, value):
    e = np.empty_like(x_s)
    if n >= 0:
        e[:n] = value
        e[n:] = x_s[:-n]
    else:
        e[n:] = value
        e[:n] = x_s[-n:]
    return e

def update_line(x_data, y_data):
    fig.set_xdata(x_data)
    fig.set_ydata(y_data)
    plt.draw()


fig = plt.plot(x, x)


while( i< size):
    #print(sensor_data_array)
    sensor_data_array = shift(sensor_data_array, -1, 5)
    update_line(x, sensor_data_array)
    i = i + 1

