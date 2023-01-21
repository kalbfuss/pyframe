#Pyframe

##Dependencies
Python
- exifread
- IPTCInfo3
- Kivy
- SQLAlchemy
- webdav3
- yaml


Raspberry Pi OS
- libxslt1.1
- libmtdev1


##Radxa zero

###Linux installation and basic configuration
Intall focal Armbian image with XFCE desktop to SD card
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

###Python configuration
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
``

###Autologin
Configure autologin of standard user.

*/etc/lightdm/lightdm.conf.d/20-autologin*
```
[Seat:*]
autologin-session=xfce   
autologin-user=langweiler
autologin-user-timeout=0
```
