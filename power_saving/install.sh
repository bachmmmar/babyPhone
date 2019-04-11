#!/bin/bash


function checkSuccess() {
    if [ $1 -ne 0 ]; then
	echo "ERROR: ${2}"
	exit 1
    else
        echo "${2}"
    fi
}


SYSTEMD_SCRIPT_DIR=/etc/systemd/system/
sudo cp rpi_no_hdmi.service $SYSTEMD_SCRIPT_DIR
checkSuccess $? "copy start script"

sudo systemctl daemon-reload
checkSuccess $? "reload script deamon"

sudo systemctl enable rpi_no_hdmi.service
checkSuccess $? "Enable hdmi disabling script"

