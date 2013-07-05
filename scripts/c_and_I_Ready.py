#!/usr/bin/python

import subprocess
import shlex
import re
import string
import time
import ConfigParser
import shlex
from subprocess import Popen,PIPE
from optparse import OptionParser

usage = "Usage: "
parser = OptionParser(usage)
parser.add_option("-c", "--config", dest="file", help="Config file for script")

(options, args) = parser.parse_args()

parser = ConfigParser.RawConfigParser()
parser.read(options.file)
path_to_ipmiutil="/usr/bin/ipmiutil"
path_to_ipmitool="/usr/bin/ipmitool"
class OCP_HW_Info (object):
    def __init__(self):
		#Extract all information from Config file#
        self.ip = parser.get('out_of_band_config', 'host_ip') #pull the IP/Hostname from the config file
        self.admin_username = parser.get('out_of_band_config', 'admin_username') #pull the admin username from the config file
        self.admin_password = parser.get('out_of_band_config', 'admin_password') #pull the admin password from the config file
        self.operator_username = parser.get('out_of_band_config','operator_username')#pull the user username from the config file
        self.operator_password = parser.get('out_of_band_config','operator_password')#pull the user password from the config file
        self.user_username = parser.get('out_of_band_config', 'user_username') #pull the operator username from the config file
        self.user_password = parser.get('out_of_band_config', 'user_password') #pull the operator password from the config file
        self.output = []
    def remote_ipmiutil_cmd(self, username, password, command): # this will run remote ipmiutil commands
        self.output = [] # set output to null
        arg = path_to_ipmiutil +" "+ command + " -N " + self.ip + " -U " + username + " -P " + password  # sets up ipmiutil command syntax
        arg = shlex.split(arg) #using shlex to get spacing correct for Popen Call
        p = Popen(arg,stdout=PIPE,stderr=PIPE)
        stdout=p.communicate()
        rc = p.returncode #gather return code from ipmiutil command
        if rc==0:
            self.output=stdout # saving output for possible future comparison
            print("this command succeeded")
        else:
            print("This command failed")

    def remote_ipmitool_cmd(self, username, password, command):
        self.output = [] #set output to null
        arg = path_to_ipmitool + " -I lanplus -H " + self.ip + " -U " + username + " -P " + password +" "+ command # sets up ipmiutil command syntax
        arg = shlex.split(arg) #using shlex to get spacing correct for Popen Call
        p = Popen(arg,stdout=PIPE,stderr=PIPE)
        stdout=p.communicate()
        rc = p.returncode #gather return  code from ipmitool command
        if rc==0:
            self.output = stdout # saving output for possible future comparision
            print("this command succeeded")
        else:
            print("This command failed")


def main():
    new = OCP_HW_Info()
    
    #Check if system is online, before we start test
    #If chassis is online, we will dothe following
    #Power reset
    ###Success criteria: Output of ipmitool command is chassis reset, andmMachine is online after 60 seconds
    #Power off
    ###Success criteria: Output of ipmitool command is chassis turned off, and Machine is offline after 60 seconds
    #Power on
    ###Success criteria: Output of ipmitool command is chassis turned on, and Machine is online after 60 seconds

    #If chassis is offline, we will do the following
    #Power on
    ###Success criteria: Output of ipmitool command is chassis turned on, and Machine is online after 60 seconds
    #Power reset
    ###Success criteria: Output of ipmitool command is chassis reset, andmMachine is online after 60 seconds
    #Power off
    ###Success criteria: Output of ipmitool command is chassis turned off, and Machine is offline after 60 seconds
    
    new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power status") #checks current status

    if new.output[0]=="Chassis Power is on\n":  
        print("Chassis is online")
        print("###Command Output= " + new.output[0])
        print("Attempting to power reset chassis")
        #Send Reset Command
        new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power reset")
        print("###Command Output= " + new.output[0])
        time.sleep(60)
        #Check Status of machine (expect on)
        new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power status")
        if new.output[0]=="Chassis Power is on\n":
            print("Chassis is online after reset")
            print("###Command Output= " + new.output[0])
            print("Attempting to power down chassis")
            #Send Power off Command
            new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power off")
            print("###Command Output= " + new.output[0])
            time.sleep(60)
            new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power status")
            print(new.output[0])
            if new.output[0]=="Chassis Power is off\n":
                print("Chassis is off after power off")
                print("###Command Output= " + new.output[0])
                print("Attempting to power on chassis")
                #Send Power on Command
                new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power on")
                print("###Command Output= " + new.output[0])
                time.sleep(60)
                #check if system is online
                new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power status")
                if new.output[0]=="Chassis Power is on\n":
                    print("OCP Ready Test Success!!!!!!!!")
            else:
                print("Error! Chassis power off failed")
        else:
            print("Error! Chassis is not online after power reset, failure")
    else:
        print("Chassis is offline")
        print("###Command Output= " + new.output[0])
        print("Attempting to power on chassis")
        #Sending Power On Command
        new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power on")
        print("###Command Output= " + new.output[0])
        time.sleep(60)
        #check if system is online
        new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power status")
        if new.output[0]=="Chassis Power is on\n":
             print("Chassis is online")
             print("###Command Output= " + new.output[0])
             print("Attempting to power reset chassis")
             #Send Reset Command
             new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power reset")
             print("###Command Output= " + new.output[0])
             time.sleep(60)
             new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power status")
             if new.output[0]=="Chassis Power is on\n":
                 print("Chassis is online after reset")
                 print("###Command Output= " + new.output[0])
                 print("Attempting to power down chassis")
                 #Send Power off Command
                 new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power off")
                 print("###Command Output= " + new.output[0])
                 time.sleep(60)
                 new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"power status")
                 print(new.output[0])
                 print("OCP Ready Test Success!!!!!!!!")

if __name__ == "__main__":
    main()
