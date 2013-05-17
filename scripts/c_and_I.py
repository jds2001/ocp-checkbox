#!/usr/bin/env python

import shlex
import re
import string
import time
import ConfigParser
import shlex
from subprocess import Popen,PIPE

parser = ConfigParser.RawConfigParser()
parser.read('ipmi_config.ini')
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
            print "this command succeeded"
        else:
            print "This command failed"

    def remote_ipmitool_cmd(self, username, password, command):
        self.output = [] #set output to null
        arg = path_to_ipmitool + " -I lanplus -H " + self.ip + " -U " + username + " -P " + password +" "+ command # sets up ipmiutil command syntax
        arg = shlex.split(arg) #using shlex to get spacing correct for Popen Call
        p = Popen(arg,stdout=PIPE,stderr=PIPE)
        stdout=p.communicate()
        rc = p.returncode #gather return  code from ipmitool command
        if rc==0:
            self.output = stdout # saving output for possible future comparision
            print "this command succeeded"
        else:
            print "This command failed"

class Remote_IPMI(object):
    def __init__(self, username, password, command):
        self.output = []
        self.return_code = []
        self.username = username
        self.password = password
        self.command = command




def main():
    new = OCP_HW_Info()
    new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"dcmi") #get DCMI capabilities with Admin User
    new.remote_ipmitool_cmd(new.user_username,new.user_password,"dcmi") #Get DCMI Capabilities with User
    new.remote_ipmitool_cmd(new.operator_username,new.operator_password,"dcmi") #Get DCMI Capabilities with Operator
    new.remote_ipmitool_cmd(new.admin_username,new.admin_password,"chassis status")
    new.remote_ipmitool_cmd(new.user_username,new.user_password,"chassis status")
if __name__ == "__main__":
    main()
