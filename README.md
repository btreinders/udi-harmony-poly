# harmony-polyglot

This is the Harmony Hub Poly for the [Universal Devices ISY994i](https://www.universal-devices.com/residential/ISY) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with  [Polyglot V2](https://github.com/Einstein42/udi-polyglotv2)
(c) JimBoCA aka Jim Searle
MIT license. 

This node server is intended to support the [Logitech Harmony Hub](http://www.logitech.com/en-us/product/harmony-hub) using the [pyharmony Python Library](https://pypi.python.org/pypi/pyharmony).

## Installation

WARNING: If you are running the v1 polyglot harmony nodeserver it will not longer work after this one is installed.  But, initially I would advise everyone to install this in a new slot and leave the old one running.  If you go back to the old one you will need manually re-install the older version of pyharmony if you have polyglot v1 and v2 running on the same machine.

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install.
3. Add NodeServer in Polyglot Web
   * After the install completes, Polyglot will reboot your ISY, you can watch the status in the main polyglot log.
4. Once your ISY is back up open the Admin Console and you should see a new node 'HarmonyController'
   * If you don't see that node, then restart the Harmony node server from the Polyglot UI.
6. The auto-discover should automatically run and find your hubs and add them.  Verify by checkig the nodeserver log.  If it doesn't then Select the HarmonyController node and click the 'Discover'.
   * While this is running you can view the nodeserver log in the Polyglot UI to see what it's doing
7. This should find your Harmony Hubs and add them to the ISY with all devices and activities
8. Once all nodes are added you will need to reboot the ISY again since the new custom profile is loaded.

### Manual Hub Entries

If the discover does not work, or you prefer to not use it, you can add customParms in the Polyglot Web UI
to tell it about your hubs.

Create a param with the name 'hub_myhubaddress' with a value: { "name": "HarmonyHub FamilyRoom", "host": "192.168.1.86" }

## Grouping the hubs

Each activity and device is created with their Hub as primary.  This makes it easy to group the devices.  Just right click on a Hub, Activity or Device node and select 'group devices'.  This makes it easy to keep them all together.

## HarmonyHub Controller

This is the main node created by this nodeserver and manages the hubs.

### Node Settings
The settings for this node are

#### Node Server Connected
   * Status of nodeserver process, this should be monitored by a program if you want to know the status
   * There is a known issue in Polyglot that upon startup, this is not always properly set.
#### Version Major
   * The major version of this nodeserver
#### Version Minor
   * The minor version of this nodeserver
#### Hubs
   * The number of hubs currently managed
#### Debug Mode
   * The debug printing mode
#### Short Poll
   * This is how often it will Poll the Hub to get the current activity
#### Long Poll
   * Not currently used
#### Profile Status
   * This is updated during commands like Discover,Install Profile, and Build Profile to show what is currently happening
      * Uninitialized = This can only happen if the node server is installed, but never ran
      * Not Sure = Can't be sure what the status is.  Currently we can not read the profile version.  Hopefully this will be added in the future
      * Discovering Hubs
      * Adding Nodes
      * Building Profile
      * Installing Profile
      * ISY Reboot Required
         * The nodeserver thinks your ISY needs rebooted.  This means a new profile was installed on the ISY, but currently we can't tell if the ISY has been rebooted, so reboot the node server after rebooting the ISY to clear this status
      * Build Profile Failed
      * Install Profile Failed
      * PyHarmony Discover Failed
      * Out of Date
      * Write profile.zip Failed
#### Activity Method
   * None = Don't watch Harmony for activity changes
   * Short Poll = Poll Harmony Hub during each Short Poll Interval (Old default method)
   * Callback = The Harmony Hub reports changes directly to the nodeserver (prefered new method)

### Node Commands

The commands for this node

#### Query
   * Poll's all hubs and sets all status in the ISY
#### Discover
   * Run's the harmony auto-discover to find your hubs, builds the profiel, and installs the profile
   * This should be run whenever you add a new hub, or update activities or devices on your hub
#### Install Profile
   * This uploads the currently built profile into the ISY.
   * Typically this is not necessary, but sometimes the ISY needs the profile uploaded twice.
#### Build Profile
   * This rebuilds the profile based on the currently managed hubs.
   * During the processes you can watch the nodeserver log (Not the polyglot log) to see what it's doing.
   * It will also update the 'Profile Status' to show what is happening from:
      * Building Profile
      * Installing Profile
      * ISY Reboot Required
   * Once it says ISY Reboot Required you should reboot the ISY.

## Harmony Hub

Each harmony hub found are configured will have a node.

## Harmony Activity

Each harmony hub activity will have a node.

## Harmony Hub

Each harmony hub device will have a node.

## Requirements

1. Polyglot V2 itself should be run on Raspian Stretch.
  To check your version, ```cat /etc/os-release``` and the first line should look like
  ```PRETTY_NAME="Raspbian GNU/Linux 9 (stretch)"```. It is possible to upgrade from Jessie to
  Stretch, but I would recommend just reimaging the SD card.  Some helpful links:
   * https://www.raspberrypi.org/blog/raspbian-stretch/
   * https://linuxconfig.org/raspbian-gnu-linux-upgrade-from-jessie-to-raspbian-stretch-9
1. This has only been tested with ISY 5.0.11B so it is not garunteed to work with any other version.

# Release Notes

- 2.1.0 01/24/2018
   - When updating the node server, click cancel so the ISY will not be rebooted, it will need to be rebooted after restarting the nodeserver.
   - Added new [Activity Method setting](https://github.com/jimboca/udi-harmony-poly/blob/master/README.md#activity-method).  Setting this to Callback should greatly stop or greatly reduce the chances of errors caused by constantly polling the hubs for current activity, and activities are updated almost instantaneously!  
   - The list of hubs is stored in hubs.json so the profile can be updated at install time.
   - All versions after this will automatically update the profile when necessary at install time. For this version when you restart the nodeserver it will rebuild the profile automatically and you will need to restart the ISY when it shows Profile Status = ISY Reboot Required
- 2.0.8 01/21/2018
   - Turn on more debug logging for pyharmony
   - Start code reorg to in preparation for move to storing known hubs in local file instead of customParams
- 2.0.7 01/21/2018
   - Fix issue with hub defined in custom params https://github.com/jimboca/udi-harmony-poly/issues/6
- 2.0.6 01/20/2018
   - Trap issues in write_profile when it fails https://github.com/jimboca/udi-harmony-poly/issues/5
- 2.0.5 01/20/2018
   - Fixed initialzation of Auto Discover mode.
- 2.0.4 01/20/2018
   - https://github.com/jimboca/udi-harmony-poly/issues/4
- 2.0.3 01/20/2018
   - profile.zip is not longer in github, renamed to profile_default.zip to avoid conflicts on update.
- 2.0.2 01/19/2018
   - Fixed Intialization of hub params
   - Allow auto-discover mode to be turned off in case it's ever needed
   - A lot of documentation added please review.
- 2.0.1 01/18/2018
   - First announced release
- 2.0.0 01/17/2018
   - Not offically released
