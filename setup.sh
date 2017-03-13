#!/bin/bash


function checkSuccess() {
    if [ $1 -ne 0 ]; then
	echo "ERROR: ${2}"
	exit 1
    else
        echo "${2}"
    fi
}


sudo -H pip3 install tornado
checkSuccess $? "Install necessary Python Weblibrary"

sudo apt-get install python3-numpy python3-scipy python3-pyaudio
checkSuccess $? "Install necessary Python library for audio and signal processing"

#sudo apt-get install libportaudio0 libportaudio2 libportaudiocpp0 portaudio19-dev
sudo apt-get install libportaudio0 libportaudio2
checkSuccess $? "Install necessary audio libraries"


IP_ADDR=$(/sbin/ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')
echo "Got IP address: $IP_ADDR"

cp index.html.template index.html
sed -i "s/%IP_ADDRESS%/$IP_ADDR/" index.html
checkSuccess $? "Replace server IP in index.html"


# Install start scripts
SYSTEMD_SCRIPT_DIR=/etc/systemd/system/
sudo cp babyPhoneWebServer.service $SYSTEMD_SCRIPT_DIR
checkSuccess $? "copy start script"

sudo cp babyPhoneAudioServer.service $SYSTEMD_SCRIPT_DIR
checkSuccess $? "copy start script"

sudo sed -i "s+%PATH_TO_SCRIPT%+$(pwd)+" ${SYSTEMD_SCRIPT_DIR}babyPhoneAudioServer.service
checkSuccess $? "Replace Path for Audio Server"

sudo sed -i "s+%PATH_TO_SCRIPT%+$(pwd)+" ${SYSTEMD_SCRIPT_DIR}babyPhoneWebServer.service
checkSuccess $? "Replace Path for Web Server"

exit 1
sudo systemctl daemon-reload
checkSuccess $? "reload script deamon"

sudo systemctl enable babyPhoneAudioServer.service
checkSuccess $? "Enable baby Phone Audio Server"

sudo systemctl enable babyPhoneWebServer.service
checkSuccess $? "Enable baby Phone Web Server"

