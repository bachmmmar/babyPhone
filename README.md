# babyPhone
A Raspberry Pi based baby sleep monitor. This is a Python 3 port of the LittleSleeper Project (https://github.com/NeilYager/LittleSleeper). A detailed documentation of LittleSleeper project is available unter http://www.aicbt.com/raspberry-pi-sleep-monitor/ . 
This Project extends the LittleSleeper by
* push notification to the mobile phone using Pushjet
* systemd services to run the application on startup
* installation script for the necessary ressources
* link to a live audio stream provided by Darkice and IceCast2


## Installation

Run the install script, which sets the device ip and ensures that all necessary tools are installed and systemd service registration.


### Live Audio Stream
To setup the live audio stream by using Darkice and IceCast2 use the following manuals.
- https://stmllr.net/blog/live-mp3-streaming-from-audio-in-with-darkice-and-icecast2-on-raspberry-pi/ 
- http://mattkaar.com/blog/2013/05/26/web-streaming-with-the-raspberry-pi-baby-monitor/

Necessary files like systemd startscripts and example configuration are provided in the audio_stream directory.

### Notification on Smartphone
You can get notification on Smartphone by using Pushjet App. Go to http://pushjet.io and register a new Service. Add the Service Secret to the .ini configuration file. Use the Public id to subscribe to the service on smartphone.
