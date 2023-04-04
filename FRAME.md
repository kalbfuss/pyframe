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

https://www.smart-things.com/de/produkte/scharge-20w-usb-c/com