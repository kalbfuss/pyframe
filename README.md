# Pyframe #

Pyframe is a Python-based digital photo frame application. It is capable of displaying photos and playing videos from local storage as well as WebDAV repositories. 

Files can be arranged in slideshows and filtered and sorted based on their metadata (EXIF and IPTC supported). Slideshows can be run continuously or scheduled.

Pyframe optionally integrates with Home Assistant via MQTT. Integration allows the display to be motion activated after coupling of the pyframe device with a motion sensor.

Pyframe is being developed by Bernd Kalbfuss (aka langweiler) and is published under the General Public License version 3. The latest source code is available on [GitHub](https://github.com/kalbfuss/pyframe).

## Dependencies ##

Pyframe requires Python 3 to run. It has been developed with Python version 3.10 on Ubuntu Linux, but may run with earlier versions and on different operating systems.

Pyframe requires the following Python packages to be installed:

- exifread
- ffmpeg-python
- IPTCInfo3
- Kivy
- paho-mqtt
- schedule
- SQLAlchemy
- webdavclient3
- yaml

All packages are available on [pypi.org](https://pypi.org) and can be installed using the *pip* command. Where possible/available, packages should be installed using the distribution package manager (e.g. *apt* on Debian/Ubuntu).

Pyframe further requires the following (non-python) libraries to be installed:

- libxslt1.1
- libmtdev1
- libsqlite3-0
- libsdl2-2.0-0
- ffmpeg

Libraries should be installed using the distribution package manager.

Note that Pyframe requires the X windows system and a desktop environment to be installed.

## Installation

Pyframe is still in early development. The easiest way to install the latest version is to clone the GitHub repository using the *git* client. After having installed the *git* client, installation of Pyframe becomes as simple as:

```bash
$ git clone git@github.com:kalbfuss/pyframe.git
```

The command installs the Pyframe sources in the sub-directory *pyframe* within the current working directory.

Pyframe can be updated to the latest version by changing into the pyframe directory and issuing the following command:

```bash
$ cd pyframe
$ git pull origin master
```

At this stage of the project you should not expect the configuration syntax to be stable. Please, have a look at the documentation after each update and adjust the configuration as necessary.

## Running Pyframe

Once Pyframe sources have been installed and all dependencies are met, the application still needs to be configured before it can be run. Please, have a look at the following section for details.

Afterwards, you can change to the Pyframe directory and start the application with the following command: 

```bash
$ python pyframe.py
```

For convenience you can install the following script under */user/local/bin*, which will allow you to start the Pyframe application from anywhere (even SSH sessions).

```bash
#!/bin/sh

USER=<your user>
SRC=<your pyframe directory>

# Set authority file and active display in case we are starting this script from an SSH session.
export XAUTHORITY=/home/$USER/.Xauthority
export DISPLAY=:0
# Change to pyframe source directory and start pyframe
cd $SRC
/usr/bin/python3 pyframe.py
# Use the following line instead if you want to start pyframe as user root, for instance via the systemctld.
# runuser -u $USER -- /usr/bin/python3 pyframe.py
```

Unless configured otherwise, Pyframe is going to create an index database *index.sqlite* and log directory *log* in the same directory. If WebDAV repositories are configured, Pyframe will further create a *cache* directory.

If you want to start Pyframe automatically after system boot, you can do so by configuring it in your desktop session manager. Alternatively, you can register a *systemctld* service via a unit file and enable it for automated start after system boot. 

You will further have to enable autologin for the user under which you intend to run the application.

## Configuration

The Pyframe application is configured via a single YAML configuration file. The file is named *config.yaml* and must be stored in the current (working) directory. The following sections provide examples for configuration and the documentation of all parameters.

A lot of effort has gone into configuration checks. The application should warn you in the event of invalid configurations immediately after startup. It is thus safe to explore the various configuration options. Under no circumstances is Pyframe going to modify any of your files.

### Examples

#### Simple configuration

In this example, we want to continuously show all files stored in a local directory. For this purpose, we configure a single local repository (*Local storage*). Our files are stored under the relative path *./local/photos*. We further define a single slideshow (*Favorites*) containing all files from the repository.  Files are shown in a random sequence for a duration of 60 s. Per (application) default settings, the repository is indexed once after start of the application. The slideshow includes photos and videos. The slideshow starts playing after start of the application. The display is always on.

```yaml
repositories:
    # Local repository with our favorite photos and videos.
    Local storage:
        type: local
        root: ./local/photos

slideshows:
    # Slideshow with our favorite photos and videos.
	Favorites:
		repositories: Local storage
		pause: 60
		sequence: random
```

#### Advanced configuration

In this example, we want to show our most recent photos stored in the cloud in the period from 8:00 to 10:00 and our favorite photos, which are stored locally, in the period from 18:00 to 20:00. Since we are not necessarily at home in the evening, we want the display to be motion activated during this time.

Firstly, we define two (enabled) repositories: A local repository (*Local storage*) with files stored under the relative path *./local/photos* and a WebDAV repository (*Cloud storage*) with files stored in the cloud. The third repository (*Test repository*) used for testing has been disabled. Per the repository default settings, the index of the local repository is updated at the start of the application and every 24 hours. The index of the cloud repository is updated daily at 23:00.

Secondly, we define two slideshows: The first slideshow (*Favorites*) includes files tagged as *favorites* from the local repository. Files are shown for a duration of 60 s. The second slideshow (*Recent*) includes the 200 most recent files from the cloud repository, which are not tagged as *vacation* or *favorites*. We further limit files to *images*. Files are sorted by the creation date in ascending order. Per the slideshow defaults, images are shown for a duration of 180 s.

The slideshow defaults further ensure that files tagged as *private* are always excluded. Files are labeled with their description from the file metadata (if available) and labels are shown for a duration of 60 s at the start and the end of each file. Since the display is installed in vertical orientation, we rotate the content by -90° and limit content to files in portrait orientation.

Thirdly, we define a schedule to show the second slideshow (*Recent*) in the time from 8:00 to 10:00 and the first slideshow (*Favorites*) in the time from 18:00 to 20:00. In the first case, the display is always on. In the second case, the display is motion activated with a timeout interval of 300 s.

Finally, since we run Home Assistant and need the MQTT remote control for the motion activation feature, we configure an MQTT client connection. For the motion activation feature to function properly, we further have to link the touch button with a motion sensor in Home Assistant (see *Motion Activation*).

```yaml
repositories:
    # Local repository with our favorite photos and videos.
    Local storage:
        type: local
        root: ./local/photos
    # WebDAV repository with the latest photos from our smartphone.
    Cloud storage:
        type: webdav
        url: https://mycloud.mydomain.org
        root: /remote.php/webdav/photos
        user: pyframe
        password: <password>
        index_update_at: "23:00"
    # Test repository, which has been disabled.
    Test repository:
        type: local
        root: ./local/test
        enabled: false

# Repository defaults
index_update_interval: 24

slideshows:
    # Slideshow with our favorite photos and videos.
	Favorites:
		repositories: Local storage
		pause: 60
		tags: favorites
	# Slideshow with most recent photos from our smartphone.
	Recent:
		repositories: Cloud storage
		excluded_tags:
			- vacation
			- favorites
		file_types: images 
		most_recent: 200
		order: descending
		sequence: date	

# Slideshow defaults
always_excluded_tags: private
label_content: description
label_mode: auto
label_duration: 30
orientation: portrait
pause: 180
rotation: -90

schedule:
	# Play the slideshow "Recent" in the period from 8:00 to 10:00.
	morning start:
		time: "08:00"
		slideshow: Recent
		display_mode: static
	morning stop:
		time: "10:00"
        play_state: stopped
	# Play the slideshow "Favorites" in the period from 18:00 to 20:00. Activate the display by motion.
	evening start:
		time: "18:00"
		slideshow: Favorites
		display_mode: motion
		display_timeout: 300
	evening stop:
		time: "20:00"
		play_state: stopped

mqtt:
	host: mqtt.local
	user: pyframe
	password: <my password>
	device_name: My pyframe somwhere in the house
```

### Application

The following parameters are used to configure the application.

#### Basic

***window_size***: The size of the window provided as *[width, height]*. A value of *full* enables full screen mode. The default is *full*.

***display_mode:*** The following display modes are supported. The default is *static*.

- *static*: The display is always on if a slideshow is paused or playing and off if a slideshow is stopped.
- *motion*: The display is turned on and the slideshow starts playing in the presence of motion. The slideshow is paused and the display turned off in the absence of motion after the display timeout interval.

***display_timeout:*** The time in seconds after which the slideshow is paused and screen turned off in the absence of motion. The default is 300 seconds.

#### Advanced

Parameters in this section will likely not have to be modified by the majority of users.

***index:*** The index database file. The path may be absolute or relative to the current working directory. The default is *./index.sqlite*.

***cache:*** The directory in which files can be cached (used by WebDAV repository). The directory path may be absolute or relative to the current working directory. The directory can be shared by multiple repositories. **Do not** use directory in which you store files as cache directory. The default is *./cache*.

***enable_exception_handler:*** Set to *off* in order to disable the generic exception handler. The generic exception handler prevents the application from exiting unexpectedly. Exceptions are logged, but the execution continues. The default is *on*.

***enable_scheduler***: Set to *off* in order to disable the scheduler. The scheduler is disabled even in the presence of a *schedule* configuration section. The default is *on*.

***enable_mqtt***: Set to *off* in order to disable the MQTT client. The client is disabled even in the presence of an *mqtt* configuration section. The default is *on*.

***enable_logging:*** Set to *off* in order to disable logging. The default is *on*.

***log_level:*** The log level, which can be set to *debug*, *info*, *warn*, or *error*. The default is *warn*.

***log_dir:*** The directory to which log files are written. The directory path may be absolute or relative to the current working directory. The default is *./log*.

### Repositories

Pyframe supports the configuration of one or multiple file repositories. Repositories are configured in the *repositories* section of the configuration file. The section is required and must contain at least a single, valid repository definition. Repository parameter defaults may be provided as global parameters.  The example below provides a typical *repositories* configuration section.

```yaml
...
repositories:
    # Local repository with our favorite photos and videos.
    Local storage:
        type: local
        root: ./local/photos
        enabled: true
    # WebDAV repository with the latest photos from our smartphone.
    Cloud storage:
        type: webdav
        url: https://mycloud.mydomain.org
        root: /remote.php/webdav/photos
        user: pyframe
        password: <password>
        enabled: false
    # Test repository, which has been disabled.
    Test repository:
        type: local
        root: ./local/test
        enabled: false

# Repository defaults
index_update_interval: 24
...
```

The following parameters are used to configure repositories.

#### General

***type:*** The following repository types are supported. A values must be provided.

- *local*: Repository with files on the local file system. **Note:** Even if referred to as *local*, files may be stored on a network share as long as the network is mounted and integrated into the file system hierarchy (e.g. */mnt/photos*).
- *webdav*: Repository with files on a WebDAV accessible site (e.g. ownCloud or NextCloud).

***index_update_interval:*** Interval in hours at which the metadata index for the repository is updated. If zero, the index is only updated once after start of the application. The default ist 0. Do not use in combination with *index_update_at*.

***index_update_at:*** The time at which the metadata index for the repository is updated. The index is updated once per day. Do not use in combination with *index_update_interval*.

***enabled:*** Set to *off* in order to disable the repository. The default is *on*.

#### Local repositories

Only a single parameter is required for the definition of local repositories.

***root***: The repository root directory. Root directories may be absolute or relative to the current working directory. Files in sub-folders will be included in the repository. A value must be provided.

#### WebDAV repositories

As a minimum, the parameters *url*, *user* and *password* need to be specified for the definition of a WebDAV repository.

***url:*** The URL of the WebDAV server. Use *https://* protocol prefix for secure connections. A value must be provided.

***user***: Login name. A value must be provided.

***password***: Login password. A value must be provided.

***root***: The root directory relative to the URL. For ownCloud WebDAV access, the root directoy typically starts with */remote.php/webdav*. The default is */*.

### Slideshows

Pyframe supports the configuration of one or multiple slideshows. Slideshows are configured in the *slideshows* section of the configuration file. The section is required and must contain at least a single, valid slideshow definition. The first slideshow is the default slideshow. Slideshow parameter defaults may be provided as global parameters. The example below provides a typical *slideshows* configuration section.

```yaml
...
slideshows:
    # Slideshow with our favorite photos and videos.
	Favorites:
		repositories: Local storage
		pause: 60
		tags: favorites
	# Slideshow with most recent photos from our smartphone.
	Recent:
		repositories: Cloud storage
		excluded_tags:
			- vacation
			- favorites
		file_types: images 
		most_recent: 200
		order: descending
		sequence: date	

# Slideshow defaults
always_excluded_tags: private
label_content: description
label_mode: auto
label_duration: 30
orientation: portrait
pause: 180
rotation: -90
...
```

The following parameters are used to configure slideshows.

#### General parameters

***bg_color:*** The background color used to fill empty areas, provided as *[r, g, b]*. The default is *[1, 1, 1]* (white).

***label_content:*** The following content based on file meta data is supported. The default is *full*.

- *description:* only image description
- *short:* image description, creation date and tags
- *full:* image description, creation date and tags, file name and repository

***label_duration:*** Duration in seconds for which labels are shown. The default is 60 seconds.

***label_font_size:*** The relative font size of labels, expressed as percentage of the shortest file dimension. The default is 0.08.

***label_mode:*** The following label modes are supported. The default is *off*.

- *auto:* Labels are shown at the beginning and end of a file for the *label_duration*.
- *off:* Labels are never shown.
- *on:* Labels are always shown.

***label_padding:*** The relative padding of labels, expressed as percentage of the shortest file dimension. The default is 0.03.

***pause:*** The delay in seconds until the next file is shown. The default is 300 seconds.

***resize:*** The following resize modes are supported. The default is *fill*.

- *fit:* The slideshow content is zoomed to fit the screen as good as possible. Empty areas are filled with the background color.
- *fill:* The slideshow content is zoomed and cropped to completely fill the screen. Note that images which do not have the same orientation as the screen are not zoomed and cropped, but only fit to the screen.

***rotation:*** The angle by which slideshow content is rotated clockwise. Useful for picture frames/screens, which are installed in non-standard orientation. The default is 0.

#### Filter criteria

The following parameters control the files included in a slideshow and the sequence in which they are shown. The default is to include all files from all repositories. Files are sorted by their name in ascending order.

***repositories:*** The repositories from which files shall be shown. The default is to show files from all repositories.

***orientation:*** Valid orientations are *portrait* or *landscape*. The default is to include either orientation.

***file_types:*** Supported file types are *images* and *videos*. May be a single value or list of values. The default is to include all file types.

***tags:*** File tags, which shall be included. May be a single value or list of values. The default is to include all tags **and** untagged files. If set, untagged files are excluded.

***excluded_tags:*** File tags, which shall be excluded. May be a single value or list of values. The default is not to exclude any tags.

***always_excluded_tags:*** Same as *excluded_tags*, but not overwritten by an *excluded_tags* statement. Use in the slideshow default configuration to exclude certain tags in all slideshows (e.g. private content).

***most_recent:*** Files in the slideshow are limited to the *most_recent* number of files based on the creation date **after** application of all other filter criteria.

***sequence:*** The sequence in which files are shown. The default is *name*.

- *date:* Files are sorted by their creation date.
- *name:* Files are sorted by their name.
- *random:* Files are shown in a random sequence.

***order:*** Valid orders are *ascending* or *descending*. The default is *ascending*. Ignored if random sequence is configured.

### Schedule

Pyframe supports the configuration of a schedule. The schedule allows to alter the application behavior at predefined points in time. The schedule is configured in the optional *schedule* section of the configuration file. The schedule may contain one or multiple events. The schedule is disabled if the configuration section is missing. The example below provides a typical *schedule* configuration section.

```yaml
schedule:
	# Play the slideshow "Recent" in the period from 8:00 to 10:00.
	morning start:
		time: "08:00"
		slideshow: Recent
		display_mode: static
	morning stop:
		time: "10:00"
        play_state: stopped
	# Play the slideshow "Favorites" in the period from 18:00 to 20:00. Activate the display by motion.
	evening start:
		time: "18:00"
		slideshow: Favorites
		display_mode: motion
		display_timeout: 30
	evening stop:
		time: "20:00"
		play_state: stopped
```

The following parameters are used to configure events in the schedule.

***time:*** The time of the event. A value must be provided. Always specify in quotation marks. Hours and minutes <10 must be preceded by a 0, i.e. "08:03" and never "8:3".

***slideshow:*** Start playing the specified slideshow. If no slideshow is specified, the previous or default slideshow is assumed.

***play_state:*** Valid play states are *paused*, *playing* and *stopped*. The play state remains unchanged if no value is provided.

***display_mode:*** The following display modes are supported. The default is *static*.

- *static*: The display is always on if a slideshow is paused or playing and off if a slideshow is stopped.
- *motion*: The display is turned on and the slideshow starts playing in the presence of motion. The slideshow is paused and the display turned off in the absence of motion after the display timeout interval.

***display_timeout:*** The time in seconds after which the slideshow is paused and screen turned off in the absence of motion. The default is 300 seconds.

### MQTT

Pyframe implements an MQTT client, which registers the device with an MQTT broker. The MQTT configuration is provided in the optional *mqtt* section of the configuration file. MQTT support is disabled if the configuration section is missing. The example below provides a typical *mqtt* configuration section.

```yaml
...
mqtt:
	host: <hostname of MQTT broker>
	user: <login name>
	password: <my password>
	device_name: My pyframe somwhere in the house
...
```

The following parameters are used to configure the MQTT client.

***host:*** Hostname of the MQTT broker. A value must be specified.

***port:*** Connection port of MQTT broker. The default is 8883 (standard for secure connections).

***tls:*** The following values are supported. The default is *on*.

- *on*: A TLS-encrypted secure connection is used.
- off: A non-encrypted connection is used.

***tls_insecure***: The following values are supported. The default is *off*.

- *on*: Insecure TLS connections with non-trusted certificates are permitted.
- *off*: Only secure connections with trusted certificates are permitted.

***user:*** Login name. A value must be provided.

***password:*** Login password. A value must be provided.

***device_id:*** The pyframe device ID. The default is *pyframe*. **Note:** The device ID must be unique. A different value must be specified if multiple pyframe instances connect to the same broker.

***device_name:*** The human friendly device name. The default is  to use the *device_id*.

## Motion activation



## Radxa Zero ##

While Pyframe in principle runs on any computer with Python 3 and the necessary libraries and packages installed, we typically want to run it on a single-board computer (SBC) that is strong enough to process photo files and play videos on-the-fly.

An ARM-based SBC, which is fit for the task, is the [Radxa Zero] (https://wiki.radxa.com/Zero). It comes with a quad-core ARM Cortex-A53 CPU, 4 GB of RAM, and up to 128 GB eMMC. It further supports OpenGL ES 3.2 and is equipped with an onboard Wifi chip. Still, it is not bigger than a Raspberry Pi Zero and thus well suited for integration into a digital photo frame.

### Linux installation and basic configuration ###

Install focal Armbian image with XFCE desktop to SD card
Boot Radxa zero from SD card
Set root password and create new user account
Open shell and start Armbian configuration tool

```
$ sudo armbian-configure
```
Adjust the following configuration settings

* Language and locale
* Keyboard layout
* Host name
* WLAN
* Auto-login

Install Armbian to eMMC using respective function in the System sub-menu.
Switch off, remove SD card and restart

Update all packages on the device
```
$ sudo apt-get update
$ sudo apt-get upgrade
```
Keep old configuration files if asked (default setting)
Reboot the device

Install ufw, allow SSH and enable ufw
```
$ sudo apt install ufw
$ sudo ufw allow OpenSSH
$ sudo ufw enable
```
Install fail2ban
```
$ sudo apt install fail2ban
```

### Python configuration ###
Install python packages via debian package manager
```
$ sudo apt install python3 python3-pip python3-kivy python3-sqlalchemy python3-yaml python3-exifread
```
Install additional packages via pip
```
$ pip3 install IPTCInfo3 webdavclient3 ffmpeg-python3
```
To enable playing of videos we further need ffmpeg and the corresponding
gstreamer plug-in.
```
$ sudo apt install ffmpeg gstreamer1.0-libav
```

#### ffpyplayer ####

On certain SBC it may be preferable to decode and display videos using
ffpyplayer instead of gstreamer.

$ sudo apt install ffmpeg libavcodec-dev libavdevice-dev libavfilter-dev libavformat-dev libavutil-dev libswscale-dev libswresample-dev libpostproc-dev libsdl2-dev libsdl2-2.0-0
libsdl2-mixer-2.0-0 libsdl2-mixer-dev python3-dev
$ pip install ffpyplayer

### Netzteil ###

https://www.smart-things.com/de/produkte/scharge-20w-usb-c/
