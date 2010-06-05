# netcfg interface...
import os.path
import os
import subprocess

helper_cmd="/usr/bin/netcfg-tray-helper"
profile_dir="/etc/network.d/"
state_dir="/var/run/network/profiles/"


def read_config(config):
    import shlex
    cfg = shlex.split(open(config, "r").read())
    options = {}
    for line in cfg:
        (var, delim, value) = line.partition('=')  
        if delim and var.lstrip()[0] != "#":
            options[var] = value
    return options


def read_rcconf(variable):
    rc=open("/etc/rc.conf")
    for line in rc.readlines():
        line=line.strip()
        if line[:len(variable)] == variable:
            key,val=line.split("=",1)
            return val.strip("'\"")

def get_profiles():
    profs= [Profile(x) for x in os.listdir(profile_dir) if not os.path.isdir(os.path.join(profile_dir,x)) ]   
    return [x for x in profs if x.has_key("CONNECTION")]
   
   
def get_active_profiles():
    profs=[Profile(x) for x in os.listdir(state_dir) if not os.path.isdir(os.path.join(state_dir,x)) ]   
    return [x for x in profs if x.has_key("CONNECTION")]
    
    
def is_profile(profile):
    return os.path.isfile(os.path.join(profile_dir, profile))


def up(profile, cmd=None, block=True, check=False):
    return run("up", profile, cmd, block, check)

    
def down(profile, cmd=None, block=True, check=False):
    return run("down", profile, cmd, block, check)


def run(func, profile, cmd=None, block=True, check=False):
    script = [helper_cmd, func, profile.name]
    if cmd:
        script.insert(0, cmd)
    process = subprocess.Popen(script, stdout=subprocess.PIPE)
    if block:
        process.wait()
    return process    
    

def auto_status(connection):
    return os.access("/var/run/daemons/net-auto-"+connection, os.F_OK)
       

def auto_interface(connection):
    
    return read_rcconf(connection.upper()+"_INTERFACE")

    
class Profile (dict):

    def __init__(self,profile_name):
        self.name=profile_name
        self.filename=os.path.join(profile_dir, profile_name)
        self.update(read_config(self.filename))

    def active(self):
        return os.path.isfile(os.path.join(state_dir,self.name))


