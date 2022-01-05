import spidev
import time
from time import sleep
import datetime
from datetime import datetime
from datetime import timedelta
import io
import fcntl
import threading
import random
import ast

#TKinter
from tkinter import *
from tkinter import ttk
import tkinter.font
#CSV file
import csv
import sys
import numpy as np
#GPIO
import RPi.GPIO as GPIO
from gpiozero import LED

#Sockets
import socket
from _thread import *
from queue import Queue

#window
win = Tk()
win.title("Water Sensors")
win['bg']=bgcolor='green'
###Window Width x Height
#win.geometry("620x350")
win.attributes('-fullscreen',True)
win.bind("<Escape>", lambda e: win.destroy())

#Variables
ph=99.9
ec=99.9
temp=99.9
ec2='--'
ec3='--'
global R1data
R1data=ec2
R2data=ec3

print_lock = threading.Lock()

"""
headers=["pH","EC","Temp","Remote1", "Remote2","Time"]
#write csv file
with open('Data.csv', 'a+') as output:
    writer = csv.writer(output, delimiter=',', lineterminator='\n')
    writer.writerow(headers)
"""

#labels

#0#
ConductivityLabel=Label(win, text=('Conductivity'), font=('calibri', 36, 'bold'),
              bg='green', fg='grey')
ConductivityLabel.place(relx=.45,rely=.2,anchor='center')

#0a#
ph_Label=Label(win, text=('pH'), font=('calibri', 36, 'bold'),
              bg='green', fg='grey')
ph_Label.place(relx=.45,rely=.55,anchor='center')

#0b#
temp_Label=Label(win, text=('Temp:'), font=('calibri', 36, 'bold'),
              bg='green', fg='grey')
temp_Label.place(relx=.35,rely=.85,anchor='center')

#1#
ecLabel=Label(win, text=('%.2f' %ec), font=('calibri', 88, 'bold'),
              bg='green')
ecLabel.place(relx=.45,rely=.35,anchor='center')

#1a#
phLabel=Label(win, text=('%.2f' %ph), font=('calibri', 88, 'bold'),
              bg='green')
phLabel.place(relx=.45,rely=.7,anchor='center')

#1b#
tempLabel=Label(win, text=('%.2f C' %temp), font=('calibri', 36, 'bold'),
              bg='green')
tempLabel.place(relx=.55,rely=.85,anchor='center')

#2#
unitLabel=Label(win, text=('μS'), font=('calibri', 88, 'bold'), fg='white',
              bg='green')
unitLabel.place(relx=.65,rely=.25)

#3#
ASULabel=Label(win, text=('ASU'), font=('calibri', 36, 'bold'), fg='red3',
              bg='green')
ASULabel.place(rely=0,relx=0)

#3#
ProdLabel=Label(win, text=('H2OSense'), font=('calibri', 36, 'bold'), fg='powder blue',
              bg='green')
ProdLabel.place(rely=0,relx=.75)


##4##
r1Label=Label(win, text=('Remote 1'), font=('calibri', 24, 'bold'),
              bg='green')
r1Label.place(relx=.1,rely=.5,anchor='center')


##5##
ec2Label=Label(win, text=('%.2s μS' %ec2), font=('calibri', 36, 'bold'),
              bg='green')
ec2Label.place(relx=.1,rely=.6,anchor='center')
ec2Label['text']='%.3s' %ec2

##6##
r2Label=Label(win, text=('Remote 2'), font=('calibri', 24, 'bold'),
              bg='green')
r2Label.place(relx=.9,rely=.5,anchor='center')


##7##
ec3Label=Label(win, text=('%.2s μS' %ec2), font=('calibri', 36, 'bold'),
              bg='green')
ec3Label.place(relx=.9,rely=.6,anchor='center')
ec3Label['text']='%.3s' %ec3


Start = datetime.now()
Nextmin = Start.minute
while Nextmin%5 != 0:
    Nextmin += 1       
    if Nextmin > 59:
        Nextmin -= 59
#global NextTime
NextTime = datetime(Start.year, Start.month, Start.day, Start.hour, Nextmin, 0)

print ("Logging will begin at ", NextTime)

# Define Atlas Scientific Sensor Class

#I2C Class Def###############################################################
class atlas_i2c:

    long_timeout = 1.5  # the timeout needed to query readings & calibrations
    short_timeout = .5  # timeout for regular commands
    default_bus = 1  # the default bus for I2C on the newer Raspberry Pis,
                     # certain older boards use bus 0
    default_address = 102  # the default address for the Temperature sensor

    def __init__(self, address=default_address, bus=default_bus):
        # open two file streams, one for reading and one for writing
        # the specific I2C channel is selected with the bus
        # it is usually 1, except for older revisions where its 0
        # wb and rb indicate binary read and write
        self.file_read = io.open("/dev/i2c-" + str(bus), "rb", buffering=0)
        self.file_write = io.open("/dev/i2c-" + str(bus), "wb", buffering=0)

        # initializes I2C to either a user specified or default address
        self.set_i2c_address(address)

    def set_i2c_address(self, addr):
        # set the I2C communications to the slave specified by the address
        # The commands for I2C dev using the ioctl functions are specified in
        # the i2c-dev.h file from i2c-tools
        I2C_SLAVE = 0x703
        fcntl.ioctl(self.file_read, I2C_SLAVE, addr)
        fcntl.ioctl(self.file_write, I2C_SLAVE, addr)

    def write(self, string):
        # appends the null character and sends the string over I2C
        string += "\00"
        self.file_write.write(bytes(string, 'UTF-8'))

    def read(self, num_of_bytes=31):
        # reads a specified number of bytes from I2C,
        # then parses and displays the result
        res = self.file_read.read(num_of_bytes)  # read from the board
        # remove the null characters to get the response
        response = list([x for x in res])

        if(response[0] == 1):  # if the response isnt an error
            # change MSB to 0 for all received characters except the first
            # and get a list of characters
            char_list = [chr(x & ~0x80) for x in list(response[1:])]
            # NOTE: having to change the MSB to 0 is a glitch in the
            # raspberry pi, and you shouldn't have to do this!
            # convert the char list to a string and returns it
            result = ''.join(char_list)
            return result.split('\x00')[0]
        else:
            return "Error " + str(response[0])  ###Edited to remove *ord()* function *str(ord(response[0]))

    def query(self, string):
        # write a command to the board, wait the correct timeout,
        # and read the response
        self.write(string)

        # the read and calibration commands require a longer timeout
        if((string.upper().startswith("R")) or
           (string.upper().startswith("CAL"))):
            sleep(self.long_timeout)
        elif((string.upper().startswith("SLEEP"))):
            return "sleep mode"
        else:
            sleep(self.short_timeout)
        return self.read()

    def close(self):
        self.file_read.close()
        self.file_write.close()
##############################################################I2C Class Def##

####Listening#Server##################################################
def Serv():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('',1234))
    s.listen(5)
    print('Localhost is '+ socket.gethostbyname(socket.gethostname())
          +'\nWaiting for a connection...')

    while True:
        print('reset loop')
        clientsocket, address = s.accept()
        clientsocket.settimeout(None)
        print(f'Connection from {address[0]} has been established!')
        
        #data = s.recv(1024)
        #print('Current sensor reading is %f ms' %data)

        msg = f'Connection established @{datetime.now():%Y-%m-%d %H:%M:%s}'
        #msg = f'{len(msg):<{HEADERSIZE}}' + msg
        
        clientsocket.send(bytes(msg,'utf-8'))

        start_new_thread(threaded_conn,(clientsocket,))
#################################################################        

######Sockets####################################################
def threaded_conn(clientsocket):
    global R1data, R2data
    while True:
        try:
            print('back in')
            recv_msg = clientsocket.recv(1024).decode('utf8')
            recv_msg = ast.literal_eval(str(recv_msg))
            print('recv_msg type is: ', type(recv_msg)) 
            print('recv_msg["Unit"]:',recv_msg["Unit"],', rec_msg["Data"]:',recv_msg['Data'])
            if recv_msg['Unit'] == 'R1':
                R1data = recv_msg['Data']
            if recv_msg['Unit'] == 'R2':
                R2data = recv_msg['Data']
            print(f'Data recieved is from remote unit {recv_msg["Unit"]}, recieved data:{recv_msg["Data"]} @{datetime.now():%Y-%m-%d %H:%M:%S}')
            clientsocket.settimeout(15)
            print('end loop')
            if not recv_msg['Unit']:
                print("No data recieved...")
                break        
        except socket.timeout:
            print("Connection lost")
            clientsocket.close()
            break
        except:
            with print_lock:
                print('No data recieved closing connection...')
            clientsocket.close()
            R1data='--'
            break
####################################################Sockets######

def readSensors():
           
    global R1data, NextTime
    while True:
        #if datetime.now() >= NextTime:
        #while True:  # Repeat the code indefinitely
                    
        # Temperature Sensor
        try:
            device = atlas_i2c(102)  
            temp_reading = device.query("R")
            temp=float(temp_reading)
            with print_lock:
                print ("Temp: %.2f" %temp)
            
            tempLabel['text']='%.2f C' %temp
        except IOError:
            temp=99
            tempLabel['text']='--'
            with print_lock:
                print ("Query failed")
        
                    
        # Electrical Conductivity Sensor
        try:
            while True:
                device = atlas_i2c(100)
                device.query("T,%.2f" %temp)

                device = atlas_i2c(100)
                ec_reading = device.query("R")
                with print_lock:
                    print ("ec_reading: %s" %ec_reading)
                if ec_reading[0].isdigit():
                    break
            with print_lock:
                print ("Cond:",ec_reading)
            ec=float(ec_reading)
            ecLabel['text']='%.2f' %ec
        except IOError:
            ec=99
            ecLabel['text']='--'
            with print_lock:
                print ("Query failed")

        # pH Sensor
        try:
            while True:
                device = atlas_i2c(99)
                device.query("T,%.2f" %temp)

                device = atlas_i2c(99)
                ph_reading = device.query("R")
                with print_lock:
                    print ("ph_reading: %s" %ph_reading)
                if ph_reading[0].isdigit():
                    break
            with print_lock:
                print ("pH:",ph_reading)
            ph=float(ph_reading)
            phLabel['text']='%.2f' %ph
        except IOError:
            ph=99
            phLabel['text']='--'
            with print_lock:
                print ("Query failed")


        #Remote 1 Update
        print('R1data: %s' %R1data)
        if R1data != '--':
            ec2Label['text']='%s' %R1data
        else:
            ec2Label['text']='--'


        #Remote 2 Update
        print('R2data: %s' %R2data)
        if R2data != '--':           
            ec3Label['text']='%s' %R2data
        else:
            ec3Label['text']='--'
            
            
            

                

            
        if datetime.now() >= NextTime:

                     
            #Parameters being logged
            timeC = time.strftime('%x %X')
            #timeC=time.strftime('%I')+':'+time.strftime('%M')+':'+time.strftime('%S')
            data=[ph, ec, temp, R1data, R2data, timeC]

            #write csv file
            with open('Data.csv', 'a+') as output:
                writer = csv.writer(output, delimiter=',', lineterminator='\n')
                writer.writerow(data)
            with print_lock:
                print('data logged time %s' %timeC)
            NextTime += timedelta(minutes=5) 

            

        
        #sleep(delay)  #Delay between sensor readings in seconds





t1 = threading.Thread(target=readSensors)
t2 = threading.Thread(target=Serv)

t1.start()
#t2.start()
        
#if __name__ == '__main__':
    #main()

#win.protocol("WM_DELETE_WINDOW", close)   ### Exit cleanly ###
win.mainloop() # Loop forever #
