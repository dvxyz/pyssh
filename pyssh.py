#!/bin/bash /usr/bin/python2.6

# T O D O
#


from optparse import OptionParser
from subprocess import call
import os
import sqlite3
import sys



def clear_screen():
	call(["clear"])



def query_yes_no(question, default="yes"):
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")



def query_agent_and_master(c, conn, cluster_id):

	agent_master = [False, False]

	c.execute ("select * from cluster where type = 'Master' and dependency = '0' and cluster_id = '" + cluster_id + "'")

	row = c.fetchone()

	# No standalone Master found, seeking an Agent-Dependant	
	if row == None:
	        c.execute ("select * from cluster where type = 'Master' and dependency = '1' and cluster_id = '" + cluster_id + "'")
	        row = c.fetchone()
		
			# No Masters at all found.
	        if row == None:
			agent_master = [False, False]
		else:
			# Does an Agent exist for this Agent-Dependant Master?
			c.execute ("select * from cluster where type = 'Agent' and cluster_id = '" + cluster_id + "'")
			row = c.fetchone()
			if row == None:
				agent_master = [False, True]
			else:
				agent_master = [True, True]
	else:
		# Standalone Master found 
		agent_master = [True, True]

	return agent_master



def add_cluster(c, conn, cluster_id, type, ip_address, password, dependency, ssh_arguments):

        admin_ui   = "https://" + cluster_id + ":10000/admin"

	try:
		with conn:
			c.execute("insert into cluster (cluster_id, address, password, ssh_arguments, admin_ui, type, dependency) \
 		                  values ('" + cluster_id + "', '" + ip_address + "', '" + password + "', '" + ssh_arguments + "', '" + admin_ui + "', '" + type + "', '" + str(dependency) + "')")
			conn.commit()

	except sqlite3.IntegrityError:
		print "couldn't add cluster twice"



def add_cluster_agent_or_master(c, conn, cluster_id, type=""):

	agent_master = query_agent_and_master(c, conn, cluster_id)

	# No Master found
	if not agent_master[1]:
		type = "Master"
	else:
		# Master found but Agent dependant - No Agent found
		if not agent_master[0]:
			type = "Agent"
		else:
			# Master (and Agent) found - no need to add any more
			# Ask for additional Agents?
			return

	ip_address = raw_input("Tell me the IP to the cluster's " + type + "\n >>> ")
	password   = raw_input("Tell me also the password for the support user\n >>> ")
	dependency = "0"
	source_port = "10000"
	dest_port   = "10000"

	# if master_or_agent("Is it a Master or an Agent?"):
	if type == "":
		type = raw_input("Is it a Master or an Agent: ")

	if type == 'Master':
		if query_yes_no("Does this Master require access through an Agent?"):
			dependency = "1"
			source_port = "12000"

	else:
		dest_port = "12000"

	ssh_arguments = source_port + ":localhost:" + dest_port

	# store = query_yes_no("Do you wish to store this information to the DB?")
	store = True
	if store:
		add_cluster(c, conn, cluster_id, type, ip_address, password, dependency, ssh_arguments)

	# Add another host recursively?
	add_cluster_agent_or_master(c, conn, cluster_id)



def delete_cluster(c, conn, cluster_id):
	c.execute("delete from cluster where cluster_id = '" + cluster_id + "'")
	conn.commit()



def update_cluster(c, conn, cluster_id):
	delete_cluster(c, conn, cluster_id)
	add_cluster_master_or_agent(c, conn, cluster_id)



def query_cluster(c, conn, cluster_id):
        c.execute ("select * from cluster where cluster_id like '" + cluster_id + "' order by dependency asc, type desc")

        for row in c.fetchall():
                ip_address = row[1]
                password   = row[2]
                ssh_arguments = row[3]

                # ssh_string = '-p \'' + password + '\' ssh support@' + ip_address + " -L " + ssh_arguments
		ssh_string = password + ' support@' + ip_address + ' ' + ssh_arguments
		print ssh_string



def print_values(c, conn, cluster_id):
        c.execute ("select * from cluster where cluster_id like '" + cluster_id + "'")
	print_rows(c.fetchall())



def print_rows(rows):
	for row in rows:
                cluster_id = row[0]
                ip_address = row[1]
                password   = row[2]
                ssh_arguments = row[3]
                admin_ui = row[4]
                type = row[5]
                dependency = str(row[6])

                ssh_string = 'sshpass -p ' + password + ' ssh support@' + ip_address + " -L " + ssh_arguments

                if type == 'Master':
                        sshpass = ssh_string

                print ""
                print "Cluster ID : " + cluster_id + " : " + type + "(" + dependency + ")"
                if type == 'Master':
                        print "Admin UI : "   + admin_ui
                print ssh_string
                print "Passwords:"
                print "\tsupport : "  + password
                print ""




parser = OptionParser()

parser.add_option("-a", "--add",    action="store_true", dest='action_add',   help='Add a Cluster')
parser.add_option("-d", "--delete", action="store_true", dest='action_del',   help='Delete a Cluster')
parser.add_option("-l", "--list",   action="store_true", dest='action_list',  help='List all Cluster')
parser.add_option("-q", "--query",  action="store_true", dest='action_query', help='Query a Cluster ID')
parser.add_option("-u", "--update", action="store_true", dest='action_upd',   help='Update a Cluster')

parser.add_option("-c", "--cluster",  dest='cluster_id', help='CLUSTER ID')
parser.add_option("--depend",         action="store_true", dest='dependency', help='Requires Access through Agents?')
parser.add_option("-i", "--ip",       dest='ip_address', help='Host or IP Address')
parser.add_option("-p", "--password", dest='password',   help='Password for support user')
parser.add_option("-s", "--ssh-arguments", dest='ssh_arguments', help='Additional SSH Arguments')
parser.add_option("-t", "--type",     dest='type',       help='Type, Agent or Master')

(options, args) = parser.parse_args()

action = ""
dependency = 0

conn = sqlite3.connect('./Lust')
c = conn.cursor()

if options.action_add:
	action = "add"
elif options.action_del:
	action = "delete"
elif options.action_query:
	action = "query"

elif options.action_upd:
	action = "update"

if options.cluster_id is None:
	if options.action_list:
		options.cluster_id = "%"
	else:
	        options.cluster_id = raw_input('Enter Cluster ID: ')


if "hosted" in options.cluster_id.lower():
	call(["./pr.sh", options.cluster_id])
else:

	if action == "add":

		if options.type is None:
       			options.type = raw_input("Enter if it's whether an Agent or a Master\n >>>")

		if options.ip_address is None:
       			options.ip_address = raw_input("Enter the IP to the cluster's " + options.type + "\n >>> ")

		if options.password is None:
		        options.password = raw_input("Enter the password for the support user\n >>> ")

		if options.dependency is None:
			dependency = 0

		elif options.dependency is True:
			dependency = 1

		if options.ssh_arguments is None:
			options.ssh_arguments = "10000:localhost:10000"

		add_cluster(c, conn, options.cluster_id, options.type, options.ip_address, options.password, dependency, options.ssh_arguments)

	if options.action_list:
		c.execute ("select * from cluster where 1=1 and cluster_id like '" + options.cluster_id + "'")
		print_rows(c.fetchall())

	elif action == "delete":
		print_values(c, conn, options.cluster_id)
		if query_yes_no("Delete this cluster's information?"):
			delete_cluster(c, conn, options.cluster_id)
	elif action == "query":
		query_cluster(c, conn, options.cluster_id)
	elif action == "update":
		update_cluster(c, conn, options.cluster_id)
		print_values(c, conn, options.cluster_id)
	else:
		add_cluster_agent_or_master(c, conn, options.cluster_id)
		print_values(c, conn, options.cluster_id)

	c.close()
