# Digital photo frame

## Building

Building your own digital photo frame is a nice project and actually not too difficult. This document provides some advice and considerations on how to achieve it. 

In essence, you only need the following components to build your own frame:

* Conventional picture frame
* Flat (portable) screen
* Linux-compatible single-board computer (SBC)
* Power supply for the screen and SBC
* Cables to connect everyting

While in principle any flat screen with the necessary ports can be used, you probably want a very flat, portable monitor to keep the entire frame as flat as possible. The disadvantage is that portable screens are (still) limited in size. An advantage is that they can usually be powered via a USB-C connection. In my case I decided for the 17.3" FHD monitor [A1 MAX](https://www.arzopa.com/products/portable-monitor-17-3-100-srgb-1080p-fhd-hdr-ips-laptop-computer-display) from Arzopa.

The picture frame I bought from the local hardware store (500x4000 mm2) and had them cut a passepartout (photo mount) fitting the portable monitor.

<img src="docs/images/frame/frame%20-%20front.jpg" alt="home assistant - device" style="zoom:50%;" />

Mounting the screen into the frame requires a bit of craftman's skills, the necessary tools (drill, saw, file, sanding paper, screw driver) and materials (wooden board, screws). Double-sided tape helps to ensure proper fit of the passepartout onto the monitor. 

I used 3D printed blocks and small screws to fix the board to the frame, but wooden blocks would have done as well. The rest is cabling. Which exact cables are required evidently depends on the components you decided to use. 

In the end, the result does not have to be pretty from the rear as long as the screen is nicely centered and fitting the passepartout. Do not forget to clean the glass before re-assembling the screen!

<img src="docs/images/frame/frame%20-%20rear.jpg" alt="home assistant - device" style="zoom:50%;" />

Regarding the SBC, there are many options available these days - most of them ARM-based and thus in principle Linux compatible. Most important for our purpose is that the SBC is sufficiently flat to fit under the photo frame. This usually excludes boards with RJ45 or stacked USB A ports. The board should further be fanless and not produce too much heat. Potentially, you will have to limit the CPU frequency.

For the local storage of files, the device should provide >32 GB of non-volatile memory in the form of an SD card or even better eMMC flash memory. If you plan to access remote repositories, the SBC evidently needs to be equipped with a Wifi chip for integration into your home network (recommended).

Most importantly, the SBC needs to be strong enough to process photos and videos on-the-fly. This requires sufficient RAM (>512 MB, but preferably >1 GB) since the texture of an unpacked photo with 4000x3000 pixels requires about 50MB of memory. For the fluent playback of videos the SBC should provide hardware accelerated decoding and resizing including the necessary **linux drivers**. Specifically the latter can be a challenge for ARM-based SBCs.

In my photo frame project, I finally decided to go with a [Radxa Zero](https://wiki.radxa.com/Zero) after initial failures with a Rasperry Pi Zero (insufficient memory) and Banana Pi Zero (missing/incomplete hardware acceleration). Further details are provided in the section below.

<img src="docs/images/frame/radxa%20zero.jpg" alt="home assistant - device" style="zoom:25%;" />

Every screen and computer require power. Overall, the problem is not too difficult to solve as long as you have a power outlet behind the frame (If yes, well planned!). Otherwise, you will have to live with a cable on the wall.

If you have a power outlet behind the frame, the challenge is to remain as flat as possible. An elegant solution to the problem is the [sCharge 12W](https://www.smart-things.com/de/produkte/scharge-12w-usb-c-unterputz-stromversorgung/) power supply from Smart Things, which integrates into the wall. The power of 12W has proven sufficient to supply the A1 Max monitor and Radxa Zero SBC.

<img src="docs/images/frame/power%20supply.jpg" alt="home assistant - device" style="zoom: 25%;" />

## Radxa Zero ##

While Pyframe in principle runs on any computer with Python 3 and the necessary libraries and packages installed, we typically want to run it on a single-board computer (SBC) that is strong enough to process photo files and play videos on-the-fly.

An ARM-based SBC, which is fit for the task, is the [Radxa Zero](https://wiki.radxa.com/Zero). It comes with a quad-core ARM Cortex-A53 CPU, 4 GB of RAM, and up to 128 GB eMMC. It further supports OpenGL ES 3.2 and is equipped with an onboard Wifi chip. Still, it is not bigger than a Raspberry Pi Zero and thus well suited for integration into a digital photo frame.

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

### Known limitations

Video processing unit

Missing DCC/CI support

Outdated armbian distribution