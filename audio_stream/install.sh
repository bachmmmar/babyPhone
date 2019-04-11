#!/bin/bash


function checkSuccess() {
    if [ $1 -ne 0 ]; then
	echo "ERROR: ${2}"
	exit 1
    else
        echo "${2}"
    fi
}


sudo apt-get install alsa-utils alsa-tools alsa-base
checkSuccess $? "Install necessary dependencies"


###### Install darkice and icecast ################
echo "IceCast: Please enter your prefered name for radio streaming host and enter a password which is later used for darkice to add the stream to IceCast"
echo "press any key to continue...."
read -n1 ans

sudo apt-get install darkice icecast2
checkSuccess $? "Install necessary dependencies"


###### Configure darkice and alsa snoop ################
sudo cp darkice.cfg /etc/
checkSuccess $? "Copy default config to etc"
echo "edit /etc/darkice.cfg: Change password (and change audio source if necessary)"
echo "press any key to continue...."
read -n1 ans


cp mic_snoop.conf /usr/share/alsa/alsa.conf.d/mic_snoop.conf
checkSuccess $? "Copy alsa mic snoop config to /usr/share/alsa/alsa.conf.d/"

./../list_audio_devices.py
echo "change slave pcm to one of the devices above in /usr/share/alsa/alsa.conf.d/mic_snoop.conf"
echo "press any key to continue...."
read -n1 ans


###### Install systemd start script for darkice ################
SYSTEMD_SCRIPT_DIR=/etc/systemd/system/
sudo cp babyPhoneDarkice.service $SYSTEMD_SCRIPT_DIR
checkSuccess $? "copy start script to $SYSTEMD_SCRIPT_DIR"

sudo systemctl daemon-reload
checkSuccess $? "reload systemd deamon"

sudo systemctl enable babyPhoneDarkice.service
checkSuccess $? "Enable baby Phone Darkice radio"
