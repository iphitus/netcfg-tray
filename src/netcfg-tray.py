#!/usr/bin/env python
 
import gtk, pygtk, gobject
import os, os.path, subprocess, sys
import netcfg
import ConfigParser, pdb

try:
    import pynotify
except ImportError:
    pynotify=False
    
profile_dir="/etc/network.d"
state_dir="/var/run/network/profiles"
helper_cmd="./netcfg-tray-helper"
config_file=os.path.expanduser(os.path.join("~/",os.environ["XDG_CONFIG_HOME"],"netcfg-tray/config"))
print config_file
license_file="/usr/share/licenses/netcfg-tray/LICENSE"
TRAY_VERSION=3


class NetcfgTray (object):
    def __init__(self):    

        self.config = ConfigParser.SafeConfigParser()
        self.config.read("/etc/xdg/netcfg-tray/config")
        self.config.read(config_file)
        self.load_config()

        self.statusIcon = gtk.StatusIcon()
        self.menu = gtk.Menu()
     
        self.action = None
     
        self.update_status_icon()
        gobject.timeout_add_seconds(5, self.update_status_icon)
        self.statusIcon.connect('popup-menu', self.popup_menu)
        self.statusIcon.set_visible(True)

        self.menu_sections=[self.menu_auto, self.menu_active, self.menu_inactive]
        
        
    def load_config(self):
        """Config file and set defaults if none available"""
        
        # Both user and 'defaults' are loaded. This will error if the defaults are broken by user or improperly installed
        n = self.config.get("notify","notify")
        if n == "libnotify" and pynotify:
            self.notifications="libnotify"
            self.libnotify=pynotify.init("netcfg-tray")
        elif n == "dzen":
            self.notifications="dzen"
            self.dzen_args = self.config.get("notify","dzen_args")
        elif n == "external" and "external_cmd" in self.config.options("notify"):
            self.notifications="external"   
        else:
            self.notifications=None

        self.root_cmd = self.config.get("main","root_cmd")


    def menu_active(self, menu):
        """Append active profile menu items to the passed menu"""
        
        item = gtk.MenuItem(label="Active profiles - click to disconnect")
        item.set_sensitive(False)
        menu.append(item)
        
        for prof in netcfg.get_active_profiles():
            item = gtk.MenuItem(label=prof.name+": "+prof["INTERFACE"]+" connected")
            item.connect('activate', self.profile_action, prof, "down")
            menu.append(item)
  
   
    def menu_auto(self, menu):
        """Append netcfg-auto-wireless entries to menu for *configured* wireless interfaces"""
        


        for connection in ["wireless","wired"]: 
            try:
                interface=netcfg.auto_interface(connection)
            except KeyError:
                return

            status=netcfg.auto_status(connection)	

            if status:
                item = gtk.MenuItem(label="Disable automatic "+connection+" ("+interface+")")
                item.connect('activate', self.profile_action, "stop", "auto-"+connection)
            else:
                item = gtk.MenuItem(label="Enable automatic "+connection+" ("+interface+")")
                item.connect('activate', self.profile_action, "start", "auto-"+connection)

    	    menu.append(item)            
    
            
    def menu_inactive(self, menu):
        """Append all inactive profiles to the menu so that they may be connected"""
        
        item = gtk.MenuItem(label="Inactive profiles - click to connect")
        item.set_sensitive(False)
        menu.append(item)
           
        for prof in netcfg.get_profiles():
            if not prof in netcfg.get_active_profiles():
                item = gtk.MenuItem(label=prof.name)
                item.connect('activate', self.profile_action, prof, "up")
                menu.append(item)


    def popup_menu(self, widget, button, time):
        """Display right click menu"""
        
        if button == 3 and not self.action:
             self.populate_menu()
             self.menu.show_all()
             self.menu.popup(None, None, None, 3, time)
             

    def populate_menu(self):    
        """Loop through all menu objects to populate main menu"""
        self.clear_menu()
            
        for section in self.menu_sections:
            # Each section is built by a separate command, run each passing the menu item
            section(self.menu)
            
            item = gtk.SeparatorMenuItem()
            self.menu.append(item)            
           
        item = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        item.connect('activate', self.about)
        self.menu.append(item)
        
        item = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        item.connect('activate', self.quit)
        self.menu.append(item)
 
 
    def clear_menu(self):
        """Clear the main menu, usually before it is updated and re-populated"""
        for item in self.menu.get_children():
            self.menu.remove(item)  
            item.destroy() # explicitly destroy so that ram usage doesnt increase with each menu popup      

    def profile_action(self, menuitem, arg, action):
        """Callback for various actions in the menu. TODO: Separate out different callback types"""
        print arg, action
        self.action = action
        
        if action == "up": # arg is a profile
            self.notify("Connecting to "+arg.name)
            self.statusIcon.set_from_stock(gtk.STOCK_CONNECT)
            process = netcfg.up(arg,block=False, cmd=self.root_cmd)
            
        elif action == "down": # arg is a profile
            self.notify("Disconnecting "+arg.name)
            process = netcfg.down(arg,block=False, cmd=self.root_cmd)
            
        elif action[:5] == "auto-": # arg is an interface
            self.notify("Auto connecting "+arg)
            self.statusIcon.set_from_stock(gtk.STOCK_CONNECT)
            script=[self.root_cmd, helper_cmd, action, arg]     
            print script
            process = subprocess.Popen(script, stdout=subprocess.PIPE)

        gobject.child_watch_add(process.pid, self.profile_action_completed, data=(arg,process))
        
         
    def profile_action_completed(self, pid, condition, args):
        """Called when the started process' stdout is closed"""
        
        profile, process = args
        
        if self.action == "up":
            if condition == 0:
                msg="Connected to "+profile.name
            else:
                msg="Connection to "+profile.name+" failed\n"+process.stdout.read()
        elif self.action == "down":
            if condition == 0:
                msg="Disconnected "+profile.name
            else:
                msg="Disconnecting "+profile.name+" failed\n"+process.stdout.read()
        elif self.action[:5] == "auto-":
            if condition == 0:
                msg="Connected "+profile
            else:
                msg="Auto connection failed \n"+process.stdout.read()
        
        self.notify(msg)
        self.action = None
        self.update_status_icon()
 
 
    def update_status_icon(self):
        """Update network profile status icon to reflect connectivity"""
        
        if self.action: # If icon has already been set by something else...
            return
        
        profiles = netcfg.get_active_profiles()
        if profiles:
            names = [ n.name for n in profiles ]
            self.statusIcon.set_tooltip("Active profiles: "+",".join(names))
            self.statusIcon.set_from_stock(gtk.STOCK_NETWORK)
        else:
            self.statusIcon.set_tooltip("No profiles active")
            self.statusIcon.set_from_stock(gtk.STOCK_DISCONNECT)
         

    def notify(self, message):
        """Output notification with whatever handler selected"""
        
        self.statusIcon.set_tooltip(message)
        if self.notifications == "libnotify":
            pynotify.Notification("netcfg-tray",message).show()
        elif self.notifications == "external":
            subprocess.Popen(self.config.get("notify","external_cmd")+" "+message, stdout=subprocess.PIPE, shell=True)       
        elif self.notifications == "dzen":
            dzen = subprocess.Popen("dzen2 " + self.dzen_args, stdin=subprocess.PIPE, shell=True)
            dzen.communicate(message+"\n")
        else:
            print message 
      
      
    def state_check(self):
        """Determine if interface is still connected"""
        active = netcfg.get_active_profiles()
        for profile in active:
            # Return codes are the reverse of True/False, hence a true here is actually a fail from grep.
            if subprocess.call("ip link show "+profile["INTERFACE"]+"|grep -q 'state UP'",shell=True):
                msg = profile.name + " appears to have been disconnected!"
                self.notify(msg)
        

    def about(self, widget, data = None):
        """Obligatory about dialog. Awesome."""
        about = gtk.AboutDialog()
        about.set_name("netcfg-tray")
        about.set_version(str(TRAY_VERSION))
        about.set_license(open(license_file).read())
        about.set_website("http://archlinux.org")
        about.set_website_label("Arch Linux")
        about.run()
        about.destroy()
    
    
    def quit(self, widget=None, data = None):
        """Um. Quit. Most tray icons actually neglect this menu item, but its useful for development"""
        gtk.main_quit()    
                
if __name__ == '__main__':
    tray = NetcfgTray()
    gtk.main()
