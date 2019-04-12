#!/bin/bash


function checkSuccess() {
    if [ $1 -ne 0 ]; then
	echo "ERROR: ${2}"
	exit 1
    else
        echo "${2}"
    fi
}


###### Install necessarry packages ################
sudo apt-get install python3-pip python3-numpy python3-scipy python3-pyaudio
checkSuccess $? "Install necessary Python library for audio and signal processing"

sudo -H pip3 install tornado
checkSuccess $? "Install necessary Python Weblibrary"

sudo apt-get install libportaudio0 libportaudio2
checkSuccess $? "Install necessary audio libraries"

###### Set own IP address in html and config ################
#IP_ADDR=$(/sbin/ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
IP_ADDR=$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)
echo "Got IP address: $IP_ADDR"

cp index.html.template index.html
sed -i "s/%IP_ADDRESS%/$IP_ADDR/" index.html
checkSuccess $? "Replace server IP in index.html"

cp babyphone.ini.template babyphone.ini
sed -i "s/%IP_ADDRESS%/$IP_ADDR/" babyphone.ini
checkSuccess $? "Replace server IP in babyphone.ini"

###### Configuration ################
echo "To use Pushjet, add the application secrete to babyphone.ini!"
echo "press any key to continue...."
read -n1 ans

./list_audio_devices.py
echo "Chose a soundcard name from above as input and ad it to babyphone.ini"
echo "press any key to continue...."
read -n1 ans

###### Install systemd start scripts ################
SYSTEMD_SCRIPT_DIR=/etc/systemd/system/
sudo cp babyPhoneWebServer.service $SYSTEMD_SCRIPT_DIR
checkSuccess $? "copy start script to $SYSTEMD_SCRIPT_DIR"

sudo cp babyPhoneAudioServer.service $SYSTEMD_SCRIPT_DIR
checkSuccess $? "copy start script to $SYSTEMD_SCRIPT_DIR"

sudo sed -i "s+%PATH_TO_SCRIPT%+$(pwd)+" ${SYSTEMD_SCRIPT_DIR}babyPhoneAudioServer.service
checkSuccess $? "Replace Path for Audio Server"

sudo sed -i "s+%PATH_TO_SCRIPT%+$(pwd)+" ${SYSTEMD_SCRIPT_DIR}babyPhoneWebServer.service
checkSuccess $? "Replace Path for Web Server"

sudo systemctl daemon-reload
checkSuccess $? "reload systemd deamon"


sudo systemctl enable babyPhoneAudioServer.service
checkSuccess $? "Enable baby Phone Audio Server"

sudo systemctl enable babyPhoneWebServer.service
checkSuccess $? "Enable baby Phone Web Server"

