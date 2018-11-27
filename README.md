# plum-probe
A tool to manage Plum LightPads without the iOS app

Dependencies:

Python 2.7.10 / Python 3.6.6+
Requests (pip install requests)

First you must initialize the local cache:
python plum-probe.py --init --username PLUM_ACCOUNT_EMAIL_ADDRESS --password YOUR_PASSWORD

If that works, you can take the logical load IDs printed out during init (or with --list) and control it --(on/off/dim/status). 
See the help: python plum-probe.py --help

You can print the local cache with python plum-probe.py --list

-If you add/remove/change the layout of your lightpads, you should reinitialize the local cache.
-You must allocate static IPs or use static DHCP to give your LightPads fixed IPs in order to avoid periodic reinitializations. The local IPs of your Plum dimmers are cached once detected to ensure minimum latency when sending commands.

OpenHAB binding here: https://github.com/mikenemat/org.openhab.binding.plum

**Note** experimental_plum_probe.py is functionally identical to plum_probe.py but with the ability --all_llid to batch apply a command to all Plum lightpads in the entire house. I do not recommend using this! Most people should just use plum_probe.py. However...it is a neat way to make all your lightpads glow the same color at the same time :)

--------------------------------------------------

**It took me a lot of work to reverse engineer this. Please share credit if you reuse the code.**

--------------------------------------------------

## Home Assistant

To use this with Home Assistant, you'll need to configure some sensors, a few shell commands and a template light.

You'll need to replace the LOGICAL_LOAD_IDS with those that are seen during the plum-probe init step.  You may also need to replace the directory "/share/source/plum-probe/" in the configuration block below if that's not where you've cloned this repo to.

This is some sample configuration:

    shell_command:
        # On at 100%
        # living_room_lights_on: 'LOGICAL_LOAD_IDS="1111111-1111-11111-1111-11111 22222-222-222-22222-22222"; cd /share/source/plum-probe/; for llid in ${LOGICAL_LOAD_IDS}; do python3 plum-probe3.py --on --logical_load_id ${llid} & done'
        # On at 50%
        living_room_lights_on: 'LOGICAL_LOAD_IDS="1111111-1111-11111-1111-111111 22222-222-222-22222-22222"; cd /share/source/plum-probe/; for llid in ${LOGICAL_LOAD_IDS}; do python3 plum-probe3.py --dim 127 --logical_load_id ${llid} & done'
        living_room_lights_off: 'LOGICAL_LOAD_IDS="11111111-1111-11111-1111-111111 22222-222-222-22222-22222"; cd /share/source/plum-probe/; for llid in ${LOGICAL_LOAD_IDS}; do python3 plum-probe3.py --off --logical_load_id ${llid} & done'
        living_room_lights_set_level: >
            /bin/bash -c 'LOGICAL_LOAD_IDS="11111111-1111-11111-1111-111111 22222-222-222-22222-22222"; 
            cd /share/source/plum-probe/; 
            for llid in ${LOGICAL_LOAD_IDS}; do 
            python3 plum-probe3.py --dim {{ brightness }} --logical_load_id ${llid}; 
            done'

    light:
        - platform: template
            lights:
            living_room_lights:
                friendly_name: "Living Room Lights"
                level_template: "{{ states.sensor.living_room_lights.state|int }}"
                value_template: "{{ states.sensor.living_room_lights.state|int > 0 }}"
                turn_on:
                service: shell_command.living_room_lights_on
                turn_off:
                service: shell_command.living_room_lights_off
                set_level:
                service: shell_command.living_room_lights_set_level
                data_template:
                    brightness: "{{ brightness }}"

    sensor:
        - platform: command_line
          command: "LOGICAL_LOAD_IDS='11111111-1111-11111-1111-111111 22222-222-222-22222-22222'; cd /share/source/plum-probe/; for llid in ${LOGICAL_LOAD_IDS}; do python3 plum-probe3.py --status --logical_load_id ${llid} | cut -d' ' -f2 | cut -d, -f1; break ; done"
          hidden: true
          name: 'living_room_lights'
          # reducce scan interval if the lag updating after lights go on or off is too long
          scan_interval: 10

### hass.io

For hass.io there are some addtional steps on your docker host

    cd /usr/share/hassio/share/
    mkdir source
    git clone <this repo>
    cd plum-probe
    # python3 plum-probe.py --init -u email -p password # to generate plum-probe.data

It's necessary to run init from the host as the docker hass container will likely be on a different subnet which will prevent broadcast discovery from working.   Once the plum-probe.data file has been generated, plum-probe.py can use the saved IPs in the file to directly to communicate with the light pads.   Also make sure you light pads have static DHCP IP assignments.
