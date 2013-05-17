 #!/bin/bash
 
 #####Script to initial OCP Roadrunner BMC#####
 
 PCIADDRESS=`lspci | grep 16b9 | awk '{print $1}'`
 echo "BMC PCI Address is "$PCIADDRESS
 MEMLOCATION=`lspci -s 03:00.6 -vvv | grep "Region 0" | awk '{print "0x"$5}'`
 echo "BMC Region 0 Memory Location is "$MEMLOCATION
 
 #remove the ipmi_si module
 rmmod ipmi_si
 echo "rmmod ipmi_si command executed"
 
 #remove the ipmi_devintf module
 rmmod ipmi_devintf
 echo "rmmod ipmi_devintf  command executed"
 
 #remove the ipmi_msghandler module
 rmmod ipmi_msghandler
 echo "rmmod ipmi_msghandler command executed"
 
 #modprobe ipmi_si with params
 modprobe ipmi_si type=kcs addrs=$MEMLOCATION regspacings=4 regsizes=1
 echo "modprobe ipmi_si type=kcs addrs=$MEMLOCATION regspacings=4 regsizes=1 command executed"
 
 #modprobe ipmi_msghandler
 modprobe ipmi_msghandler
 echo "modprobe ipmi_msghandler command executed"
 
 #modprobe ipmi_devintf
 modprobe ipmi_devintf
 echo "modprobe ipmi_devintf command executed"