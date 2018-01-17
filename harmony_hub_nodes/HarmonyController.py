#
# HarmonyController
#
# TODO:
# - discover should check if hub IP address has changed?
# - Set longpoll from our driver. (need getDriver)
#
# This is the main Harmony Hub Node Controller  
# Add a Configuration Parameter:
# Key=hub_FamilyRoom
# Value={ "name": "HarmonyHub FamilyRoom", "host": "192.168.86.82" }
# Key=hub_MasterBedroom
# Value={ "name": "HarmonyHub MasterBedroom", "host": "192.168.86.80" }
#

import polyinterface
import json,re,time,sys,os.path,yaml
from traceback import format_exception
from harmony_hub_nodes import HarmonyHub
from harmony_hub_version import VERSION_MAJOR,VERSION_MINOR
from harmony_hub_funcs import uuid_to_address,long2ip
from write_profile import write_profile

LOGGER = polyinterface.LOGGER
CONFIG = "config.yaml"

# Read the SERVER info from the json.
with open('server.json') as data:
    SERVERDATA = json.load(data)
try:
    VERSION = SERVERDATA['credits'][0]['version']
except (KeyError, ValueError):
    LOGGER.info('Version not found in server.json.')
    VERSION = '0.0.0'

class HarmonyController(polyinterface.Controller):
    """
    The Controller Class is the primary node from an ISY perspective. It is a Superclass
    of polyinterface.Node so all methods from polyinterface.Node are available to this
    class as well.

    Class Variables:
    self.nodes: Dictionary of nodes. Includes the Controller node. Keys are the node addresses
    self.name: String name of the node
    self.address: String Address of Node, must be less than 14 characters (ISY limitation)
    self.polyConfig: Full JSON config dictionary received from Polyglot.
    self.added: Boolean Confirmed added to ISY as primary node

    Class Methods (not including the Node methods):
    start(): Once the NodeServer config is received from Polyglot this method is automatically called.
    addNode(polyinterface.Node): Adds Node to self.nodes and polyglot/ISY. This is called for you
                                 on the controller itself.
    delNode(address): Deletes a Node from the self.nodes/polyglot and ISY. Address is the Node's Address
    longPoll(): Runs every longPoll seconds (set initially in the server.json or default 10 seconds)
    shortPoll(): Runs every shortPoll seconds (set initially in the server.json or default 30 seconds)
    query(): Queries and reports ALL drivers for ALL nodes to the ISY.
    runForever(): Easy way to run forever without maxing your CPU or doing some silly 'time.sleep' nonsense
                  this joins the underlying queue query thread and just waits for it to terminate
                  which never happens.
    """
    def __init__(self, polyglot):
        """
        Optional.
        Super runs all the parent class necessities. You do NOT have
        to override the __init__ method, but if you do, you MUST call super.
        """
        self.l_info('init','Initializing VERSION=%s' % (VERSION))
        super(HarmonyController, self).__init__(polyglot)
        self.name = 'HarmonyHub Controller'
        self.address = 'harmonyctrl'
        self.primary = self.address
        
    def start(self):
        """
        Optional.
        Polyglot v2 Interface startup done. Here is where you start your integration.
        This will run, once the NodeServer connects to Polyglot and gets it's config.
        In this example I am calling a discovery method. While this is optional,
        this is where you should start. No need to Super this method, the parent
        version does nothing.
        """
        self.l_info('start','Starting Config=%s' % (self.polyConfig))

        self.setDriver('GV1', VERSION_MAJOR)
        self.setDriver('GV2', VERSION_MINOR)
        # Set Profile Status as Up To Date
        # TODO: Need a way to know this...
        # TODO: Get driver, only if it's reboot required, then set to 1?
        self.setDriver('GV7', 1)
        #
        #
        self.l_debug("start","longPoll={}".format(self.polyConfig['longPoll']))
        #
        # Add Hubs from the config
        #
        self.l_debug("start","Adding hubs...")
        self._set_num_hubs(0)
        #self.l_debug("start","nodes={}".format(self.polyConfig['nodes']))
        if self.polyConfig['nodes']:
            self.load_config()
            for item in self.polyConfig['nodes']:
                if item['isprimary'] and item['node_def_id'] != self.id:
                    self.l_debug("start","adding hub for item={}".format(item))
                    self.add_hub_from_customData(item['address'])
        else:
            # No nodes exist, that means this is the first time we have been run after install
            # So, do a discover
            self.discover()
           

    def shortPoll(self):
        """
        Optional.
        This runs every 10 seconds. You would probably update your nodes either here
        or longPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        #self.l_debug('shortPoll','...')
        pass

    def longPoll(self):
        """
        Optional.
        This runs every 30 seconds. You would probably update your nodes either here
        or shortPoll. No need to Super this method the parent version does nothing.
        The timer can be overriden in the server.json.
        """
        #self.l_debug('longpoll','...')
        pass

    def query(self):
        """
        Optional.
        By default a query to the control node reports the FULL driver set for ALL
        nodes back to ISY. If you override this method you will need to Super or
        issue a reportDrivers() to each node manually.
        """
        self.l_debug('query','...')
        for node in self.nodes:
            if self.nodes[node].address != self.address and self.nodes[node].do_poll:
                self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        """
        Example
        Do discovery here. Does not have to be called discovery. Called from example
        controller start method and from DISCOVER command recieved from ISY as an exmaple.
        """
        hub_list = list()
        self._set_num_hubs(0)
        #
        # Look for the hubs...
        #
        self.setDriver('GV7', 2)
        self.l_info('discover','harmony_discover: starting...')
        from pyharmony import discovery as harmony_discovery
        harmony_discovery.logger = LOGGER
        try:
            res = harmony_discovery.discover(scan_attempts=10,scan_interval=1)
        except (OSError) as err:
            self.setDriver('GV7', 9)
            self.l_error('discover','pyharmony discover failed. Please restart this nodeserver: {}'.format(err))
            return
        self.l_info('discover','harmony_discover: {0}'.format(res))
        #
        # Add the nodes
        #
        self.setDriver('GV7', 3)
        #
        # First from customParams
        #
        for param in self.polyConfig['customParams']:
            match = re.match( "hub_(.*)", param, re.I)
            if match is not None:
                address = match.group(1)
                self.l_info('discover','got param {0} address={1}'.format(param,address))
                cfg = self.polyConfig['customParams'][param]
                try:
                    cfgd = json.loads(cfg)
                except:
                    err = sys.exc_info()[0]
                    self.l_error('discover','failed to parse cfg={0} Error: {1}'.format(cfg,err))
                addit = True
                if not 'name' in cfgd:
                    self.l_error('discover','No name in customParam {0} value={1}'.format(param,cfg))
                    addit = False
                if not 'host' in cfgd:
                    self.l_error('discover','No host in customParam {0} value={1}'.format(param,cfg))
                    addit = False
                if addIt:
                    hub_list.append({'address': address, 'name': cfgd['name'], 'host': cfgd['host'], 'port': 5222})
                    self._set_num_hubs(self.num_hubs + 1)
                    
        #
        # Next the discovered ones
        #
        for config in res:
            hub_list.append(
                {
                    'address': uuid_to_address(config['uuid']),
                    'name':    config['friendlyName'],
                    'host':    config['ip'],
                    'port':    config['port']
                }
            )
        #
        # Now really add them.
        #
        for cnode in hub_list:
            self.add_hub(cnode['address'], cnode['name'], cnode['host'], cnode['port'])
        #
        # Build the profile
        #
        self.setDriver('GV7', 4)
        # This writes all the profile data files and returns our config info.
        # TODO: Need to zip up all files...
        config_data = write_profile(LOGGER,hub_list)
        # Reload the config we just generated.
        self.load_config()
        #
        # Upload the profile
        #
        self.setDriver('GV7', 5)
        try:
            self.poly.installprofile()
        except:
            # I know... don't catch all, but I don't know what possiblities there are?
            err = sys.exc_info()[0]
            self.setDriver('GV7', 7)
            self.l_error('discovery','Install Profile Error: {}'.format(err))
            return
        # Now a reboot is required
        # TODO: This doesn't really mean it was complete, a response is needed from polyglot,
        # TODO: which is on the enhancement list.
        self.setDriver('GV7', 6)

    def add_hub(self,address,name,host,port,save=True):
        self.l_debug("add_hub","address={0} name='{1}' host={2} port={3} save={4}".format(address,name,host,port,save))
        self.addNode(HarmonyHub(self, address, name, host, port))
        self._set_num_hubs(self.num_hubs + 1)
        if save:
            cdata = self.polyConfig['customData']
            if not 'hubs' in cdata:
                cdata['hubs'] = {}
            cdata['hubs'][address] = {'name': name, 'host': host, 'port': port}
            self.saveCustomData(cdata)

    def add_hub_from_customData(self,address):
        self.l_debug("add_hub_from_customData","Hub address {0}".format(address))
        cdata = self.polyConfig['customData']
        self.l_debug("add_hub_from_customData","customData={0}".format(cdata))
        if 'hubs' in cdata:
            if address in cdata['hubs']:
                ndata = cdata['hubs'][address]
                return self.add_hub(address,ndata['name'],ndata['host'],ndata['port'])
        self.l_error("add_hub_from_customData","Hub address {0} not saved in customData={1}".format(address,cdata))

    def load_config(self):
        if os.path.exists(CONFIG):
            self.l_info('load_config','Loading Harmony config {}'.format(CONFIG))
            try:
                config_h = open(CONFIG, 'r')
                self.harmony_config = yaml.load(config_h)
                config_h.close
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_str = ''.join(format_exception(exc_type, exc_value, exc_traceback))
                self.l_error('load_config','failed to parse cfg={0} Error: {1}'.format(CONFIG,err_str))
        else:
            self.l_error('load_config','Harmony config does not exist {}'.format(CONFIG))
        
    def delete(self):
        """
        Example
        This is sent by Polyglot upon deletion of the NodeServer. If the process is
        co-resident and controlled by Polyglot, it will be terminiated within 5 seconds
        of receiving this message.
        """
        self.l_info('delete','Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def _set_num_hubs(self, value):
        self.num_hubs = value
        self.l_info("_set_num_hubs","{}".format(self.num_hubs))
        self.setDriver('GV3', self.num_hubs)
        return True

    def get_node_driver(self,node,driver):
        self.l_debug("get_node_driver","driver={0} node={1}".format(driver,node))
        if node['drivers']:
            for nd in node['drivers']:
                if nd['driver'] == driver:
                    self.l_debug("get_node_driver","driver={0} found={1}".format(driver,nd))
                    return nd
        self.l_debug("get_node_driver","driver={1} Not Found".format(driver))
        return False
    
    def l_info(self, name, string):
        LOGGER.info("%s:%s: %s" %  (self.id,name,string))
        
    def l_error(self, name, string):
        LOGGER.error("%s:%s: %s" % (self.id,name,string))
        
    def l_warning(self, name, string):
        LOGGER.warning("%s:%s: %s" % (self.id,name,string))
        
    def l_debug(self, name, string):
        LOGGER.debug("%s:%s: %s" % (self.id,name,string))

    """
    Optional.
    Since the controller is the parent node in ISY, it will actual show up as a node.
    So it needs to know the drivers and what id it will use. The drivers are
    the defaults in the parent Class, so you don't need them unless you want to add to
    them. The ST and GV1 variables are for reporting status through Polyglot to ISY,
    DO NOT remove them. UOM 2 is boolean.
    """
    id = 'HarmonyController'
    commands = {
        'QUERY': query,
        'DISCOVER': discover,
#        'REFRESH_CONFIG': _cmd_refresh_config,
#        'SET_DEBUGMODE': _cmd_set_debug_mode,
#        'SET_SHORTPOLL': _cmd_set_shortpoll,
#        'SET_LONGPOLL':  _cmd_set_longpoll
    }
    """ 
       Driver Details:
    """
    drivers = [
        {'driver': 'ST',  'value': 0, 'uom': 2},  #    bool:   Connection status (managed by polyglot)
        {'driver': 'GV1', 'value': 0, 'uom': 56}, #   float:   Version of this code (Major)
        {'driver': 'GV2', 'value': 0, 'uom': 56}, #   float:   Version of this code (Minor)
        {'driver': 'GV3', 'value': 0, 'uom': 25}, # integer: Number of the number of hubs we manage
        {'driver': 'GV4', 'value': 0, 'uom': 25}, # integer: Log/Debug Mode
        {'driver': 'GV5', 'value': 0, 'uom': 25}, # integer: shortpoll
        {'driver': 'GV6', 'value': 0, 'uom': 25}, # integer: longpoll
        {'driver': 'GV7', 'value': 0, 'uom': 25}  #    bool: Profile status
    ]
