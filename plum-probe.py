import requests
import argparse
import sys
import base64
import pickle
import hashlib
from socket import *
from time import sleep

requests.packages.urllib3.disable_warnings()

__author__ = "Mike Nemat"

parser = argparse.ArgumentParser(description="This script connects to the Plum API to retrieve the necessary tokens and UUIDs to control Plum Lightpad switches on a local network without the Plum app\n\nNote: You MUST give your LightPads static IPs, ideally using static DHCP, in order for non-Plum app control of your LightPads to work reliably")

groups = parser.add_mutually_exclusive_group(required=True)
groups.add_argument("-i","--init",help="Use --init the first time you run this app, or any time you add/remove/change your Plum LightPad layout",action="store_true")
groups.add_argument("-l","--list",help="List all Plum lightpads in the currently cached layout", required=False,action="store_true")
groups.add_argument("--logical_load_id", help="The logical load ID to control. A logical load is either one or more Plum switches that control the same load")

parser.add_argument("-u","--username",help="Your Plum username (email address)", required=False,default="")
parser.add_argument("-p","--password",help="Your Plum password", required=False, default="")

ops = parser.add_mutually_exclusive_group(required=False)
ops.add_argument("--on",help="Turn on the Plum LightPad", required=False, action="store_true", default=False)
ops.add_argument("--off",help="Turn off the Plum LightPad", required=False, action="store_true", default=False)
ops.add_argument("--dim",help="Dim the Plum LightPad to specified level (0 to 255)", type=int, required=False, default=-1)
ops.add_argument("--glow_force",help="Force the glow on for an amount of time WITHOUT persisting the color. MUST be in the format INTENSITY,TIME,R,G,B,W. Intensity=0-100,TIME=SECONDS,R=0-255,G=0-255,B=0-255,W=0-255 example --glow_force 100,20,255,0,0,0 to force the lightpad to glow red at full brightness for 20 seconds", required=False, default="")
ops.add_argument("--glow_timeout",help="Set the glow timeout (how long the glow stays on after a motion event, value must be in seconds", type=int, required=False, default=-1)
ops.add_argument("--glow_intensity",help="Set the glow intensity (brightness), value must be an integer 0-100", type=int, required=False, default=-1)
ops.add_argument("--glow_color",help="Set the glow color. MUST BE IN THE FORMAT --glow_color R,G,B,W with R,G,B,W standing for Red,Green,Blue,White respectively, values 0-255 for each. WARNING: Certain values like 255,255,255,255 seem to disable the glow. Set it back to 255,0,0,0 and verify it is red if you suspect you passed in a value it didn't like", required=False, default="")
ops.add_argument("--glow_enable",help="Enable glow on motion for the logical load", action="store_true", required=False, default=False)
ops.add_argument("--glow_disable",help="Disable glow on motion for the logical load", action="store_true", required=False, default=False)
ops.add_argument("--status",help="Return the status of the Plum Lightpad", action="store_true", required=False, default=False)

args = parser.parse_args()

def data_for_logical_load(llid, plum_dict):
	for h,house in plum_dict["house"].items():
		for r,room in house["rooms"].items():
			for l,load in room["logical_loads"].items():
				if l == llid:
					for p,pads in load["lightpads"].items():
						token = house["token"]
						h = hashlib.new("sha256")
						h.update(token.encode("utf-8"))
						token = h.hexdigest()
						return {"ip":plum_dict["network"][p]["ip"],"port":plum_dict["network"][p]["port"],"token":token}
					
	raise Exception("Couldn't find LLID")
					

def plum_list(plum_dict):
	house_dict = plum_dict["house"]
	replies = plum_dict["network"]
	for h,house in house_dict.items():
		print("House: %s" % (house["name"]))
		print("\tHouse ID: %s" % (h))
		print("\tHouse Token: %s" % (house["token"]))
		print("")
		print("\tRooms:")
		for r,room in house["rooms"].items():
			print("\t\tRoom: %s" % (room["name"]))
			print("\t\t\tRoom ID: %s" % (r))
			for l,load in room["logical_loads"].items():
				print("\t\t\tLogical Load: %s" % (load["name"]))			
				print("\t\t\t\tLogical Load ID: %s" % (l))			
				print("")
				print("\t\t\t\tLightpads:")
				for p, lightpad in load["lightpads"].items():
					print("\t\t\t\t\tLightpad ID: %s" % (p))
					try:
						print("\t\t\t\t\tLightpad IP: %s" % (replies[p]["ip"]))
						print("\t\t\t\t\tLightpad Port: %s" % (replies[p]["port"]))
					except:
						print ("\t\t\t\t\tWARNING Did not find LightPad on local network!!!")
				
					print ("")
def plum_rest(url, post, headers):
	r = requests.post(url, headers=headers, json=post)
	return r.json()

def plum_command(url, post, headers):
	r = requests.post(url, headers=headers, json=post, verify=False)
	return r.status_code

def plum_local_rest(url, post, headers):
	r = requests.post(url, headers=headers, json=post, verify=False)
	return r.json()

def plum_parse(json, key, map, ref):
	values = {}
	for k,v in map.items():
		values.update({k:json[v]})

	ref.update({key:values})

if args.logical_load_id and args.on == False and args.off == False and args.dim == -1 and args.status == False and len(args.glow_color) == 0 and args.glow_enable == False and args.glow_disable == False and args.glow_intensity == -1 and args.glow_timeout == -1 and len(args.glow_force) == 0:
	print ("You must provide on/off/dim/status along with your logical load ID to execute a command")
	print ("example --logical_load_id 123345677-23525-2525-252525255 --dim 255")
	sys.exit(3)

if args.init and (len(args.username) == 0 or len(args.password) == 0):
	print ("You must specifiy your Plum username and password when initializing")
	print ("example --init -u bob@gmail.com -p hunter2")
	sys.exit(1)

if args.init:
	print ("Probing local network for Plum lightpads... This may take around 30 seconds.")
	print ("")

	count = 0
	replies = {}
	
	for i in range(1,6):
		cs = socket(AF_INET, SOCK_DGRAM)
		cs.bind(("", 50000))
		cs.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
		cs.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
		cs.sendto('PLUM'.encode(),('255.255.255.255', 43770))
		cs.settimeout(5)
		try:
			while True:
				data,ip = cs.recvfrom(10000)
				parsed = data.decode().split(" ")
				lpid = parsed[2]
				if lpid not in replies:
					count = count + 1
					print ("Found %d LightPads so far..." % (count))
					lpid_dict = {}
					lpid_dict.update({"port":parsed[3]})
					lpid_dict.update({"ip":ip[0]})
					replies.update({lpid:lpid_dict})
		except:
			pass
		finally:
			cs.close()

	print ("")
	print ("Retrieving layout from Plum cloud servers...")
	print ("")


	auth_string = base64.b64encode(("%s:%s" % (args.username, args.password)).encode())

	house_dict = {}

	headers = {
	    'User-Agent': 'Plum/2.3.0 (iPhone; iOS 9.2.1; Scale/2.00)',
	    'Authorization': "Basic %s" % (auth_string.decode()),
	}

	try:
		response = requests.get('https://production.plum.technology/v2/getHouses', headers=headers).json()
	except:
		print ("Received error logging in to Plum. This is most likely due to an invalid username or password!")
		sys.exit(5)

	for house in response :
		reply1 = plum_rest("https://production.plum.technology/v2/getHouse", {"hid":house}, headers)
		plum_parse(reply1, house, {"name":"house_name","token":"house_access_token"}, house_dict)

		rooms = {}
		house_dict[house].update({"rooms":rooms})

		for room in reply1["rids"]:
			reply2 = plum_rest("https://production.plum.technology/v2/getRoom", {"rid":room}, headers)
			plum_parse(reply2, room, {"name":"room_name"}, rooms)

			llids = {}
			house_dict[house]["rooms"][room].update({"logical_loads": llids})

			for llid in reply2["llids"]:
				reply3 = plum_rest("https://production.plum.technology/v2/getLogicalLoad", {"llid":llid}, headers)
				plum_parse(reply3, llid, {"name":"logical_load_name"}, llids)
				
				lpids = {}
				house_dict[house]["rooms"][room]["logical_loads"][llid].update({"lightpads":lpids})

				for lpid in reply3["lpids"]:
					reply4 = plum_rest("https://production.plum.technology/v2/getLightpad", {"lpid":lpid}, headers)
					plum_parse(reply4, lpid, {"name":"lightpad_name"}, lpids)

	plum_dict = {}
	plum_dict.update({"house":house_dict})
	plum_dict.update({"network":replies})
	plum_list(plum_dict)
	pickle.dump(plum_dict, open("plum-probe.data","wb"))
	sys.exit(0)
	
plum_dict = {}

if args.list or args.on or args.dim >= 0 or args.off or args.status or args.glow_enable or args.glow_disable or len(args.glow_color) > 0 or args.glow_intensity >= 0 or args.glow_timeout >=0 or len(args.glow_force) > 0:
	try:
		plum_dict = pickle.load(open("plum-probe.data","rb"))
	except:
		print ("Unable to read plum-probe.data....are you sure you've initialized it by running python plum-probe.py --init --username USER--password PASS ?????")
		sys.exit(2)

if args.list:
	plum_list(plum_dict)
	sys.exit(0)
try:
	data = data_for_logical_load(args.logical_load_id, plum_dict)
except:
	print ("Error finding the data for this logical load. Either the logical load ID is invalid or this switch wasn't detected on your network. Reinitialize the database using --init")
	sys.exit(4)

headers = {
	'User-Agent': 'Plum/2.3.0 (iPhone; iOS 9.2.1; Scale/2.00)',
	'X-Plum-House-Access-Token': data["token"]
}

if args.on:
	ret = plum_command("https://%s:%s/v2/setLogicalLoadLevel" % (data["ip"],data["port"]), {"level":255,"llid":args.logical_load_id}, headers)
if args.off:
	ret = plum_command("https://%s:%s/v2/setLogicalLoadLevel" % (data["ip"],data["port"]), {"level":0,"llid":args.logical_load_id}, headers)
if args.dim >= 0:
	ret = plum_command("https://%s:%s/v2/setLogicalLoadLevel" % (data["ip"],data["port"]), {"level":args.dim,"llid":args.logical_load_id}, headers)
if args.glow_intensity >= 0:
	ret = plum_command("https://%s:%s/v2/setLogicalLoadConfig" % (data["ip"],data["port"]), {"config":{"glowIntensity":(float(args.glow_intensity)/float(100))},"llid":args.logical_load_id}, headers)
if args.glow_timeout >= 0:
	ret = plum_command("https://%s:%s/v2/setLogicalLoadConfig" % (data["ip"],data["port"]), {"config":{"glowTimeout":args.glow_timeout},"llid":args.logical_load_id}, headers)
if len(args.glow_force) > 0:
	forceValues = args.glow_force.split(",")
	intensity = int(forceValues[0].strip())
	time = int(forceValues[1].strip())
	red = int(forceValues[2].strip())
	green = int(forceValues[3].strip())
	blue = int(forceValues[4].strip())
	white = int(forceValues[5].strip())

	ret = plum_command("https://%s:%s/v2/setLogicalLoadGlow" % (data["ip"],data["port"]), {"intensity":(float(intensity)/float(100)),"timeout":time * 1000,"red":red,"white":white,"blue":blue,"green":green,"llid":args.logical_load_id}, headers)
if args.glow_enable:
	ret = plum_command("https://%s:%s/v2/setLogicalLoadConfig" % (data["ip"],data["port"]), {"config":{"glowEnabled":True},"llid":args.logical_load_id}, headers)
if args.glow_disable:
	ret = plum_command("https://%s:%s/v2/setLogicalLoadConfig" % (data["ip"],data["port"]), {"config":{"glowEnabled":False},"llid":args.logical_load_id}, headers)
if len(args.glow_color) > 0:
	colorValues = args.glow_color.split(",")
	red = int(colorValues[0].strip())
	green = int(colorValues[1].strip())
	blue = int(colorValues[2].strip())
	white = int(colorValues[3].strip())
	
	ret = plum_command("https://%s:%s/v2/setLogicalLoadConfig" % (data["ip"],data["port"]), {"config":{"glowColor":{"red":red,"white":white,"blue":blue,"green":green}},"llid":args.logical_load_id}, headers)
if args.status:
	ret = plum_local_rest("https://%s:%s/v2/getLogicalLoadMetrics" % (data["ip"],data["port"]), {"llid":args.logical_load_id}, headers)
	print (ret)
else:
	if ret == 204:
		print ("SUCCESS")
	else:
		print ("FAIL %d" % (ret))
