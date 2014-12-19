#!/bin/bash

PYSSH="python2.6 $HOME/pyssh.py"
SSHPASS=~/.sshpass/bin/sshpass

function ssh_connect() {
 password=$1
 ip_host=$2
 tunnel=$3

 .sshpass/bin/sshpass -p ${password} ssh ${ip_host} -L ${tunnel} 
}


if [ $# -eq 0 ]; then
 $SSHPASS -h
fi


cluster_id=${1:-""}


# sshpass.sh <cluster_id>
# if cluster exists, return sshpass command
# else, ask for connection information as now.

if [ $# -eq 1 ]; then

 sshstring=`$PYSSH --query --cluster=$cluster_id`

 ssh_connect $sshstring

 exit

fi


if [ $# -gt 3 ] ; then

 password=${2:-""}
 ip_host=${4:-""}
 tunnel=${6:-"10000:localhost:10000"}
 cluster_type="Master"

 ssh_connect $password $ip_host $tunnel

 if [ $? == 0 ] ; then

  address=${ip_host#*@}
  echo "Address: ${address}"

  if [ $tunnel == "10000:localhost:11000" ] ; then
   type=Agent
  fi
 
  $PYSSH --add --ip=$address --ssh-arguments=$tunnel --password=$password --type=$cluster_type

 fi

fi
